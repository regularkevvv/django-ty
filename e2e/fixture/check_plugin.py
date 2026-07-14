from typing_extensions import reveal_type

from library.models import Author, Book

reveal_type(Book(title="Dune").title)
reveal_type(Book.objects.filter(title__icontains="dune"))
reveal_type(Book.objects.get(author__name="Ada"))
reveal_type(Book.objects.values("title"))
reveal_type(Book.objects.values_list("title", flat=True))
reveal_type(Author().books)

Book.objects.filter(pages__icontains="wrong")
