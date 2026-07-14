from django.db.models import Manager, QuerySet

from library.models import Author, Book

book = Book(title="Dune")
title: str = book.title
books: QuerySet[Book, Book] = Book.objects.filter(title__icontains="dune")
fetched: Book = Book.objects.get(author__name="Ada")
titles: QuerySet[Book, str] = Book.objects.values_list("title", flat=True)
related: Manager[Book] = Author().books
