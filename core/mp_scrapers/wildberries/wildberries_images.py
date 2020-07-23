import time

from django.core.files.base import ContentFile
from django.db import connection, transaction
from django.utils.timezone import now

from core.models import Image
from core.mp_scrapers.wildberries.wildberries_base import WildberriesBaseScraper
from core.types import RequestBody
from core.utils.logging_helpers import get_logger

logger = get_logger()


class WildberriesImageScraper(WildberriesBaseScraper):
    def update_from_mp(self) -> None:
        start = time.time()
        connection.close()
        image = self._get_image_to_download()

        if image is not None:
            self._download_image_and_update_fields(image)
        logger.debug(f'Done in {time.time() - start:0.0f} seconds')

    def _get_image_to_download(self) -> Image:
        with transaction.atomic():
            image = Image.objects.select_for_update(skip_locked=True).filter(
                mp_source=self.mp_source, next_parse_time__lte=now(), start_parse_time__isnull=True).order_by(
                'next_parse_time').first()
            if image is not None:
                self._update_start_parse_time(image)
                return image

    @staticmethod
    def _update_start_parse_time(image: Image) -> None:
        image.start_parse_time = now()
        image.save()

    def _download_image_and_update_fields(self, image: Image) -> None:
        img_bytes, _, status_code = self.connector.get_page(RequestBody(image.mp_link, 'get', parsing_type='image'))
        if status_code == 200:
            image.image_file.save(image.mp_link.split('/')[-1], ContentFile(img_bytes), save=False)
        else:
            logger.error(f'Can not find image on link {image.mp_link}')
        image.next_parse_time = now() + image.parse_frequency
        image.start_parse_time = None
        image.save()
