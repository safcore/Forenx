from rest_framework import serializers
from .models import Case


class CaseSerializer(serializers.ModelSerializer):
    investigator_username = serializers.CharField(source="investigator.username", read_only=True)
    investigator_name = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = "__all__"
        read_only_fields = ("investigator",)

    def get_investigator_name(self, obj):
        if not obj.investigator:
            return ""
        full_name = f"{obj.investigator.first_name} {obj.investigator.last_name}".strip()
        return full_name or obj.investigator.username