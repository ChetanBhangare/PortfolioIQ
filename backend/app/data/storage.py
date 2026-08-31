from abc import ABC,abstractmethod
from io import BytesIO
from pathlib import Path
import json,boto3,pandas as pd
from botocore.exceptions import ClientError

class StorageBackend(ABC):
    @abstractmethod
    def read_parquet(self,key): ...
    @abstractmethod
    def write_parquet(self,key,df): ...
    @abstractmethod
    def exists(self,key): ...
    @abstractmethod
    def write_json(self,key,payload): ...
    @abstractmethod
    def read_json(self,key): ...

class LocalStorage(StorageBackend):
    def __init__(self,root): self.root=Path(root)
    def _path(self,key): return self.root/key
    def read_parquet(self,key):
        p=self._path(key); return pd.read_parquet(p) if p.exists() else pd.DataFrame()
    def write_parquet(self,key,df):
        p=self._path(key); p.parent.mkdir(parents=True,exist_ok=True); df.to_parquet(p,index=False)
    def exists(self,key): return self._path(key).exists()
    def write_json(self,key,payload):
        p=self._path(key); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(payload,indent=2,default=str))
    def read_json(self,key):
        p=self._path(key); return json.loads(p.read_text()) if p.exists() else None

class S3Storage(StorageBackend):
    def __init__(self,settings):
        if not settings.s3_bucket: raise ValueError("S3_BUCKET required when STORAGE_MODE=s3")
        self.bucket=settings.s3_bucket; self.prefix=settings.s3_prefix.strip("/")
        session=boto3.Session(profile_name=settings.aws_profile or None,region_name=settings.aws_region)
        self.client=session.client("s3")
    def _key(self,key): return f"{self.prefix}/{key.strip('/')}".strip("/")
    @staticmethod
    def _is_missing(error):
        code=str(error.response.get("Error",{}).get("Code",""))
        return code in {"404","NoSuchKey","NotFound"}
    def exists(self,key):
        try:
            self.client.head_object(Bucket=self.bucket,Key=self._key(key)); return True
        except ClientError as e:
            if self._is_missing(e): return False
            raise
    def read_parquet(self,key):
        try: obj=self.client.get_object(Bucket=self.bucket,Key=self._key(key))
        except ClientError as e:
            if self._is_missing(e): return pd.DataFrame()
            raise
        return pd.read_parquet(BytesIO(obj["Body"].read()))
    def write_parquet(self,key,df):
        b=BytesIO(); df.to_parquet(b,index=False); b.seek(0); self.client.put_object(Bucket=self.bucket,Key=self._key(key),Body=b.getvalue(),ContentType="application/vnd.apache.parquet")
    def write_json(self,key,payload): self.client.put_object(Bucket=self.bucket,Key=self._key(key),Body=json.dumps(payload,indent=2,default=str).encode(),ContentType="application/json")
    def read_json(self,key):
        try: obj=self.client.get_object(Bucket=self.bucket,Key=self._key(key))
        except ClientError as e:
            if self._is_missing(e): return None
            raise
        return json.loads(obj["Body"].read())

def get_storage(settings): return S3Storage(settings) if settings.storage_mode.lower()=="s3" else LocalStorage(settings.local_data_path)
