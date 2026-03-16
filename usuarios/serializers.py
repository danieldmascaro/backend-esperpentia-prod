from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseDjoserUserSerializer
from rest_framework import serializers

from .models import Comuna, Region, Usuario


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ("id", "nombre")


class ComunaSerializer(serializers.ModelSerializer):
    region = RegionSerializer(read_only=True)
    region_id = serializers.PrimaryKeyRelatedField(queryset=Region.objects.all(), source="region", write_only=True)

    class Meta:
        model = Comuna
        fields = ("id", "nombre", "county_code", "region", "region_id")


class UsuarioRegionComunaValidationMixin:
    def validate(self, attrs):
        attrs = super().validate(attrs)
        region = attrs.get("region", getattr(self.instance, "region", None))
        comuna = attrs.get("comuna", getattr(self.instance, "comuna", None))

        if comuna and region and comuna.region_id != region.id:
            raise serializers.ValidationError({"comuna": "La comuna debe pertenecer a la region seleccionada."})

        return attrs


class UsuarioSerializer(UsuarioRegionComunaValidationMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    region = RegionSerializer(read_only=True)
    comuna = ComunaSerializer(read_only=True)
    region_id = serializers.PrimaryKeyRelatedField(queryset=Region.objects.all(), source="region", required=False, allow_null=True)
    comuna_id = serializers.PrimaryKeyRelatedField(queryset=Comuna.objects.select_related("region"), source="comuna", required=False, allow_null=True)

    class Meta:
        model = Usuario
        fields = (
            "email",
            "nombre",
            "apellido",
            "direccion_entrega",
            "region",
            "region_id",
            "comuna",
            "comuna_id",
            "password",
        )

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = Usuario(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class SuperUsuarioSerializer(UsuarioRegionComunaValidationMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    region = RegionSerializer(read_only=True)
    comuna = ComunaSerializer(read_only=True)
    region_id = serializers.PrimaryKeyRelatedField(queryset=Region.objects.all(), source="region", required=False, allow_null=True)
    comuna_id = serializers.PrimaryKeyRelatedField(queryset=Comuna.objects.select_related("region"), source="comuna", required=False, allow_null=True)

    class Meta:
        model = Usuario
        fields = (
            "email",
            "nombre",
            "apellido",
            "direccion_entrega",
            "region",
            "region_id",
            "comuna",
            "comuna_id",
            "password",
            "is_active",
            "is_staff",
            "is_superuser",
        )

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        validated_data.setdefault("is_staff", True)
        validated_data.setdefault("is_superuser", True)

        user = Usuario(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class DjoserUserCreateSerializer(UsuarioRegionComunaValidationMixin, BaseUserCreateSerializer):
    region_id = serializers.PrimaryKeyRelatedField(queryset=Region.objects.all(), source="region", required=False, allow_null=True)
    comuna_id = serializers.PrimaryKeyRelatedField(queryset=Comuna.objects.select_related("region"), source="comuna", required=False, allow_null=True)

    class Meta(BaseUserCreateSerializer.Meta):
        model = Usuario
        fields = ("id", "email", "nombre", "apellido", "direccion_entrega", "region_id", "comuna_id", "password")


class DjoserUserSerializer(UsuarioRegionComunaValidationMixin, BaseDjoserUserSerializer):
    region = RegionSerializer(read_only=True)
    comuna = ComunaSerializer(read_only=True)
    region_id = serializers.PrimaryKeyRelatedField(queryset=Region.objects.all(), source="region", required=False, allow_null=True)
    comuna_id = serializers.PrimaryKeyRelatedField(queryset=Comuna.objects.select_related("region"), source="comuna", required=False, allow_null=True)

    class Meta(BaseDjoserUserSerializer.Meta):
        model = Usuario
        fields = ("id", "email", "nombre", "apellido", "direccion_entrega", "region", "region_id", "comuna", "comuna_id")
