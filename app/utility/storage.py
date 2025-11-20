from fastapi import UploadFile
from supabase import create_client, Client
from app.config.environments import SUPABASE_PROJECT_URL, SUPABASE_SERVICE_KEY

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_PROJECT_URL, SUPABASE_SERVICE_KEY)


async def upload_to_supabase_storage(
        file: UploadFile,
        filename: str,
        bucket: str = "videos"
) -> str:
    """
    Upload a file to Supabase Storage

    Args:
        file: UploadFile object from FastAPI
        filename: Name to save the file as
        bucket: Supabase storage bucket name (default: "videos")

    Returns:
        str: Public URL of the uploaded file

    Raises:
        Exception: If upload fails
    """
    try:
        # Read file content
        file_content = await file.read()

        # Upload to Supabase Storage
        response = supabase.storage.from_(bucket).upload(
            path=filename,
            file=file_content,
            file_options={
                "content-type": file.content_type or "application/octet-stream",
                "upsert": "false"  # Don't overwrite existing files
            }
        )

        # Get public URL
        public_url = supabase.storage.from_(bucket).get_public_url(filename)

        return public_url

    except Exception as e:
        raise Exception(f"Failed to upload to Supabase Storage: {str(e)}")


async def upload_file_to_supabase_storage(
        file_content: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        bucket: str = "videos"
) -> str:
    """
    Upload file content (bytes) to Supabase Storage

    Args:
        file_content: File content as bytes
        filename: Name to save the file as
        content_type: MIME type of the file
        bucket: Supabase storage bucket name (default: "videos")

    Returns:
        str: Public URL of the uploaded file

    Raises:
        Exception: If upload fails
    """
    try:
        # Upload to Supabase Storage
        response = supabase.storage.from_(bucket).upload(
            path=filename,
            file=file_content,
            file_options={
                "content-type": content_type,
                "upsert": "false"  # Don't overwrite existing files
            }
        )

        # Get public URL
        public_url = supabase.storage.from_(bucket).get_public_url(filename)

        return public_url

    except Exception as e:
        raise Exception(f"Failed to upload to Supabase Storage: {str(e)}")


async def delete_from_supabase_storage(file_path: str, bucket: str = "videos") -> bool:
    try:
        if file_path.startswith("http"):
            filename = file_path.split("/")[-1]
        else:
            filename = file_path

        supabase.storage.from_(bucket).remove([filename])

        return True

    except Exception as e:
        print(f"Error deleting file from Supabase Storage: {str(e)}")
        return False


def get_file_url(filename: str, bucket: str = "videos") -> str:
    return supabase.storage.from_(bucket).get_public_url(filename)


async def create_signed_url(filename: str, expires_in: int = 3600, bucket: str = "videos") -> str:
    try:
        response = supabase.storage.from_(bucket).create_signed_url(
            path=filename,
            expires_in=expires_in
        )
        signed = response["signedURL"]

        if "?" in signed:
            signed += f"&download={filename}"
        else:
            signed += f"?download={filename}"

        return signed

    except Exception as e:
        raise Exception(f"Failed to create signed URL: {str(e)}")