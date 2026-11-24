from .models import HotelConfig

def hotel_context(request):

    config, created = HotelConfig.objects.get_or_create(id=1)
    return {'hotel': config}