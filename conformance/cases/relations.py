from typing_extensions import assert_type

from conformance_models.models import Author, Book, Category, Tag, User


assert_type(Book().author, Author)  # conformance: relations.foreign-key-one-to-one/foreign-key-read expect=pass
assert_type(Book().author_id, int)  # conformance: relations.foreign-key-one-to-one/foreign-key-id expect=pass
assert_type(User().edited_book, Book)  # conformance: relations.foreign-key-one-to-one/reverse-one-to-one expect=pass

assert_type(Book().tags.get(), Tag)  # conformance: relations.many-to-many/forward-manager-result expect=pass
assert_type(Tag().books.get(), Book)  # conformance: relations.many-to-many/reverse-manager-result expect=pass

assert_type(Author().books.get(), Book)  # conformance: relations.reverse-relations/reverse-foreign-key expect=pass
assert_type(Category().children.get(), Category)  # conformance: relations.reverse-relations/reverse-self-relation expect=pass

assert_type(Book().editor, User | None)  # conformance: relations.string-settings-targets/settings-target expect=pass
assert_type(Category().parent, Category | None)  # conformance: relations.string-settings-targets/self-target expect=pass

Author.objects.filter(authored_book__title="Dune")  # conformance: relations.related-query-name/related-query-traversal expect=pass
Author.objects.filter(unknown_book__title="Dune")  # conformance: relations.related-query-name/invalid-related-query-name expect=fail
