from rest_framework import serializers

from waitlist.models import WaitList


class WaitListSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitList
        fields = [
            "id",
            "fullname",
            "email",
            "is_developer",
            "role",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]

    def validate_email(self, value):
        return value.lower().strip()

    def validate_fullname(self, value):
        return value.strip()
