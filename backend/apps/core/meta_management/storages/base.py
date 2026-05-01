from abc import ABC, abstractmethod


class StorageBackend(ABC):

    name = ''

    @abstractmethod
    def build_storage_key(self, hint):
        raise NotImplementedError

    @abstractmethod
    def issue_presigned_upload(self, storage_key, policy):
        raise NotImplementedError

    @abstractmethod
    def head(self, storage_key):
        raise NotImplementedError

    @abstractmethod
    def delete(self, storage_key):
        raise NotImplementedError

    @abstractmethod
    def resolve_url(self, asset, viewer=None, ttl_seconds=300):
        raise NotImplementedError

    @abstractmethod
    def put_object(self, storage_key, body, mime_type=''):
        raise NotImplementedError
