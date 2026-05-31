from rest_framework import serializers

from .models import Nomenclature


class NomenclatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nomenclature
        fields = '__all__'
