from django_query_profiler.client.context_manager import QueryProfiler
from django_query_profiler.query_profiler_storage import QueryProfilerLevel

from core.mp_scrapers.wildberries.wildberries_items import WildberriesIncrementItemScraper


def start_profiler():
    scraper = WildberriesIncrementItemScraper()
    with QueryProfiler(QueryProfilerLevel.QUERY_SIGNATURE) as qp:
        scraper.update_from_mp()

    print(qp.query_profiled_data.summary)
    print('\n')

    for query_signature, query_signature_statistics in qp.query_profiled_data.query_signature_to_query_signature_statistics.items():
        print(query_signature_statistics)
        print('\n')
        print(query_signature.query_without_params)
        print(query_signature.analysis)
        print('==' * 80)
