from accounts.models import User
from library.models import Author, Book

author = Author(name="Ada")
user = User(email="ada@example.com", display_name="Ada")

Book(title=123, author=author, editor=user)
bad_title: int = Book.objects.get(title="Dune").title
bad_pages_lookup = Book.objects.filter(pages__icontains="many")
missing_lookup = Book.objects.filter(missing_field="x")
bad_relation_lookup = Book.objects.filter(author__missing="x")
bad_values = Book.objects.values("missing_field")
bad_values_list = Book.objects.values_list("missing_field", flat=True)
