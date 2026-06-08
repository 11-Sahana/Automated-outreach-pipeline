from abc import ABC, abstractmethod
from typing import Optional

from outreach.models import Contact, VerifiedEmail


class EmailProvider(ABC):

    @abstractmethod
    def find_email(self, contact: Contact) -> Optional[VerifiedEmail]:
        ...

    @property
    def provider_name(self) -> str:
        return self.__class__.__name__