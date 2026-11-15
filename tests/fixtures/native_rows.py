from datetime import datetime
from typing import assert_type
from conformance_models.models import Article
assert_type(Article.objects.values().get()["title"], str)  # conformance: querysets.lazy-rows/dict-field expect=pass
assert_type(Article.objects.values().get()["created_at"], datetime)  # conformance: querysets.lazy-rows/dict-inherited expect=pass
assert_type(Article.objects.values_list(named=True).get().title, str)  # conformance: querysets.lazy-rows/named-field expect=pass
assert_type(Article.objects.values_list(named=True).get().created_at, datetime)  # conformance: querysets.lazy-rows/named-inherited expect=pass
wrong_dict: int = Article.objects.values().get()["title"]  # conformance: querysets.lazy-rows/dict-wrong-type expect=fail
wrong_named: int = Article.objects.values_list(named=True).get().title  # conformance: querysets.lazy-rows/named-wrong-type expect=fail
