from django_query_profiler.client.context_manager import QueryProfiler
from django_query_profiler.query_profiler_storage import QueryProfilerLevel

from core.models import ItemCategory
from core.mp_scrapers.wildberries.wildberries_items import WildberriesItemScraper


def start_profiler():
    scraper = WildberriesItemScraper()
    category = ItemCategory.objects.get(id=17674)
    with QueryProfiler(QueryProfilerLevel.QUERY_SIGNATURE) as qp:
        scraper._process_all_pages(category, counter=77, debug=True)

    print(qp.query_profiled_data.summary)
    print('\n')

    # for query_signature, query_signature_statistics in qp.query_profiled_data.query_signature_to_query_signature_statistics.items():
    #     print(query_signature_statistics)
    #     print('\n')
    #     print(query_signature.query_without_params)
    #     print(query_signature.analysis)
    #     print('==' * 80)
