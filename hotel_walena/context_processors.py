from django.db import DatabaseError
from hotel_walena.models import HotelConfig


def hotel_context(request):
    try:
        config, _ = HotelConfig.objects.get_or_create(id=1)
    except DatabaseError:
        config = None
    return {'hotel': config}