from rest_framework import serializers

from waitlist.models import AnalyticsEvent, EmailDeliveryLog, EmailTemplate, WaitList


class WaitListSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(source="name", required=False, write_only=True)

    class Meta:
        model = WaitList
        fields = [
            "id",
            "name",
            "fullname",
            "email",
            "is_developer",
            "role",
            "source",
            "status",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]
        extra_kwargs = {
            "name": {"required": False},
            "source": {"required": False},
            "status": {"required": False},
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is None and not attrs.get("name"):
            raise serializers.ValidationError({"name": ["This field is required."]})
        return attrs

    def validate_email(self, value):
        return value.lower().strip()

    def validate_name(self, value):
        return value.strip()


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = [
            "id",
            "subject",
            "body",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class EmailDeliveryLogSerializer(serializers.ModelSerializer):
    subscriber_id = serializers.PrimaryKeyRelatedField(
        queryset=WaitList.objects.all(),
        source="subscriber",
        write_only=True,
    )
    subscriber = WaitListSerializer(read_only=True)

    class Meta:
        model = EmailDeliveryLog
        fields = [
            "id",
            "subscriber",
            "subscriber_id",
            "recipient_email",
            "subject",
            "body",
            "status",
            "error_message",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "subscriber",
            "recipient_email",
            "subject",
            "body",
            "created_at",
        ]
        extra_kwargs = {
            "status": {"required": False},
            "error_message": {"required": False},
        }

    def create(self, validated_data):
        subscriber = validated_data["subscriber"]
        template = (
            EmailTemplate.objects.filter(is_active=True).order_by("-created_at").first()
        )
        subject = template.subject if template else "Welcome to WaitForIt"
        body = (
            template.body if template else "Thanks for joining the WaitForIt waitlist."
        )

        return EmailDeliveryLog.objects.create(
            subscriber=subscriber,
            recipient_email=subscriber.email,
            subject=subject,
            body=body,
            status=validated_data.get("status", EmailDeliveryLog.Status.QUEUED),
            error_message=validated_data.get("error_message", ""),
        )


class AnalyticsEventSerializer(serializers.ModelSerializer):
    subscriber_id = serializers.PrimaryKeyRelatedField(
        queryset=WaitList.objects.all(),
        source="subscriber",
        required=False,
        allow_null=True,
        write_only=True,
    )
    subscriber = WaitListSerializer(read_only=True)

    class Meta:
        model = AnalyticsEvent
        fields = [
            "id",
            "event",
            "subscriber",
            "subscriber_id",
            "visitor_id",
            "metadata",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "subscriber",
            "created_at",
        ]
        extra_kwargs = {
            "visitor_id": {"required": False},
            "metadata": {"required": False},
        }
