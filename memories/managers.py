from pathlib import PurePath as Path
from typing import TYPE_CHECKING

from django.db.models import QuerySet, manager

if TYPE_CHECKING:
    from authentication.models import User
    from memories.models import Capsule


class CapsuleManager(manager.Manager):
    def create(
        self,
        title,
        description,
        capsule: "Capsule",
        image_file: "Path" | None = None,
        video_file: "Path" | None = None,
        log: "str" | None = None,
    ) -> Capsule:
        capsule.title = title

        capsule.description = description

        if image_file is not None:
            capsule.image = image_file

        if video_file is not None:
            capsule.video = video_file

        if log is not None:
            capsule.log = log
        capsule.save(using=self._db)

    def add_members(self: QuerySet["Capsule"], pk=None, user_id=None) -> "User":
        capsule = self.model.objects.get(id=pk)
        user = User.objects.get(id=user_id)
        capsule.members.add(user)
        return capsule.members

    def add_contributors(self: QuerySet["Capsule"], pk=None, user_id=None) -> "User":
        capsule = self.model.objects.get(id=pk)
        user = User.objects.get(id=user_id)
        capsule.contributors.add(user)
        return capsule.contributors
