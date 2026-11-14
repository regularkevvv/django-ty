from typing import assert_type
from conformance_models.models import Book, BookProxy

assert_type(Book.objects.values("title").get(id=1)["title"], str)  # conformance: querysets.lazy-rows/dict-field expect=pass
assert_type(BookProxy.objects.values("title").get(id=1)["title"], str)  # conformance: querysets.lazy-rows/dict-inherited expect=pass
assert_type(Book.objects.values_list("title", named=True).get(id=1).title, str)  # conformance: querysets.lazy-rows/named-field expect=pass
assert_type(BookProxy.objects.values_list("title", named=True).get(id=1).title, str)  # conformance: querysets.lazy-rows/named-inherited expect=pass
wrong_dict: int = Book.objects.values("title").get(id=1)["title"]  # conformance: querysets.lazy-rows/dict-wrong-type expect=fail
wrong_named: int = Book.objects.values_list("title", named=True).get(id=1).title  # conformance: querysets.lazy-rows/named-wrong-type expect=fail
