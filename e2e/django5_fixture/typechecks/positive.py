from accounts.models import Profile, User
from commerce.models import Invoice, Order
from library.models import Author, Book, Category, Tag

user = User(email="ada@example.com", display_name="Ada")
profile = Profile(user=user, bio="math", reputation=10)
author = Author(name="Ada", age=None)
category = Category(name="Science")
tag = Tag(label="classic")
book = Book(
    title="Dune",
    pages=412,
    author=author,
    editor=user,
    category=category,
)

created = Book.objects.create(
    title="Foundation",
    pages=255,
    author=author,
    editor=user,
    category=category,
)

title: str = book.title
pages: int | None = book.pages
book_id: int = book.id
book_pk: int = book.pk
author_id: int = book.author_id
author_name: str = book.author.name
tag_label: str = tag.label

maybe_editor = book.editor
if maybe_editor is not None:
    editor_email: str = maybe_editor.email

book.author = author
book.author_id = 1
book.editor = None
book.editor_id = None

profile_user_email: str = user.profile.user.email
edited_title: str = user.edited_books.get(title="Dune").title
reverse_book_title: str = author.books.get(title="Dune").title
child_category = Category(name="Speculative", parent=category)
child_name: str = category.children.get(name="Speculative").name
tagged_title: str = tag.books.get(title="Dune").title

filtered_title: str = Book.objects.filter(title__icontains="du").get().title
excluded_author: Author = Book.objects.exclude(title="Dune").get().author
published_title: str = Book.published.filter(author__name="Ada").get().title
first_book: Book | None = Book.objects.filter(pages__isnull=True).first()
latest_book: Book = Book.objects.latest("id")
book_count: int = Book.objects.count()
has_books: bool = Book.objects.exists()
created_pair: tuple[Book, bool] = Book.objects.get_or_create(
    title="Dune",
    author=author,
    editor=user,
)
updated_pair: tuple[Book, bool] = Book.objects.update_or_create(
    title="Dune",
    defaults={"pages": 413},
)

title_value: str = Book.objects.values_list("title", flat=True).get()
page_tuple: tuple[str, int | None] = Book.objects.values_list("title", "pages").get()
named_page: int | None = Book.objects.values_list("title", "pages", named=True).get().pages
row_title: str = Book.objects.values("title").get()["title"]
score: int = Book.objects.annotate(score=1).get().score

all_title: str = Book.objects.all().get(title="Dune").title
ordered_title: str = Book.objects.order_by("title").get(title="Dune").title
distinct_title: str = Book.objects.distinct().get(title="Dune").title
only_title: str = Book.objects.only("title").get(title="Dune").title
deferred_title: str = Book.objects.defer("pages").get(title="Dune").title
selected_title: str = Book.objects.select_related("author").get(title="Dune").title
prefetched_title: str = Book.objects.prefetch_related("tags").get(title="Dune").title

order = Order(customer=user, book=book, quantity=2, note=None)
invoice = Invoice(order=order, external_id="inv-1")
invoice_order_book_title: str = invoice.order.book.title
order_invoice_external_id: str = order.invoice.external_id
customer_order_title: str = user.orders.get(book__title="Dune").book.title
created_title: str = created.title
if child_category.parent is not None:
    child_parent_name: str = child_category.parent.name
