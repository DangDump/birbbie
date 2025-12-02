import aioboto3
from botocore.config import Config

from PIL import Image
from io import BytesIO
import discord
import logging
import os
from datetime import datetime, timezone, timedelta
import asyncio



logger = logging.getLogger(__name__)

s3_client = None
if (
    os.getenv("R2_URL")
    and os.getenv("ACCESS_KEY_ID")
    and os.getenv("SECRET_ACCESS_KEY")
    and os.getenv("BUCKET")
):
    s3_client = aioboto3.Session()

async def CompressImage(image_bytes: bytes) -> bytes:
    img = Image.open(BytesIO(image_bytes))
    img = img.convert("RGB")
    output = BytesIO()
    img.save(output, format="JPEG", quality=50)
    return output.getvalue()


async def CompressVideo(video_bytes: bytes) -> bytes:
    input_file = BytesIO(video_bytes)
    output_file = BytesIO()

    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i", "pipe:0",
        "-vcodec", "libx264",
        "-crf", "30",
        "-movflags", "+faststart+frag_keyframe+empty_moov",
        "-f", "mp4",
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate(input_file.read()) 

    if process.returncode != 0:
        return b""

    output_file.write(stdout)
    return output_file.getvalue()

async def upload_file_to_r2(
    file_bytes: bytes, filename: str, message: discord.Message
) -> str:
    if s3_client is None:
        return ""

    async with s3_client.client(
        service_name="s3",
        endpoint_url=os.getenv("R2_URL"),
        aws_access_key_id=os.getenv("ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="weur",
    ) as client:

        if filename.lower().endswith(("png", "jpg", "jpeg", "gif", "bmp")):
            file_bytes = await CompressImage(file_bytes)
            content_type = "image/jpeg"
        elif filename.lower().endswith(("mp4", "avi", "mov", "webm", "mkv")):
            content_type = "video/mp4"
            max_size = int(os.getenv('MAX_FILE_SIZE', 25 * 1024 * 1024))
            if len(file_bytes) > max_size:
                return ""
        elif filename.lower().endswith(("mp3", "wav", "ogg")):
            content_type = "audio/mpeg"
        else:
            content_type = "application/octet-stream"

        await client.upload_fileobj(
            BytesIO(file_bytes),
            os.getenv("BUCKET"),
            f"{message.id}/{filename}",
            ExtraArgs={"ContentType": content_type},
        )

        return f"{os.getenv('FILE_URL')}/{message.id}/{filename}"

async def ClearOldFiles():
    if s3_client is None:
        return

    async with s3_client.client(
        service_name="s3",
        endpoint_url=os.getenv("R2_URL"),
        aws_access_key_id=os.getenv("ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="weur",
    ) as client:

        continuation_token = None

        while True:
            list_params = {"Bucket": os.getenv("BUCKET")}
            if continuation_token:
                list_params["ContinuationToken"] = continuation_token

            response = await client.list_objects_v2(**list_params) 

            if "Contents" in response:
                delete_keys = []
                for obj in response["Contents"]:
                    last_modified = obj["LastModified"]
                    file_extension = obj["Key"].split(".")[-1].lower()

                    if file_extension in ["mp4", "avi", "mov", "webm"] and (
                        datetime.now(timezone.utc) - last_modified > timedelta(days=int(os.getenv('VIDEO_DAYS', 7)))
                    ):
                        delete_keys.append({"Key": obj["Key"]})

                    elif (datetime.now(timezone.utc) - last_modified) > timedelta(days=int(os.getenv('IMAGE_DAYS', 35))):
                        delete_keys.append({"Key": obj["Key"]})

                if delete_keys:
                    await client.delete_objects(
                        Bucket=os.getenv("BUCKET"), Delete={"Objects": delete_keys}
                    )  

            continuation_token = response.get("NextContinuationToken")
            if not continuation_token:
                break
