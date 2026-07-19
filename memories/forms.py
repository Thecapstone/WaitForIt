from django import forms
from memories.models import Capsule


class CapsuleContentForm(forms.ModelForm):
    class Meta:
        model = Capsule
        fields = ["title", "description", "private"]
