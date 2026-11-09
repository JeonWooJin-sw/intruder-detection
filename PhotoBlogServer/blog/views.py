from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F
from django.db.models.functions import TruncDate
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .forms import PostForm
from .models import Post
from .permissions import IsAuthorOrReadOnly
from .serializers import PostSerializer


def post_list(request):
    # 최신 글이 위로 오도록 변경 (원래는 오래된 글이 위)
    posts = Post.objects.filter(
        published_date__lte=timezone.now()
    ).order_by('-published_date')
    return render(request, 'blog/post_list.html', {'posts': posts})


def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    return render(request, 'blog/post_detail.html', {'post': post})


@login_required
def post_new(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.published_date = timezone.now()
            post.save()
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm()
    return render(request, 'blog/post_edit.html', {'form': form})


@login_required
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden('작성자만 수정할 수 있습니다.')
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            # 원래 코드는 수정한 사람으로 author가 바뀌어서 author는 그대로 둠
            post = form.save(commit=False)
            post.published_date = timezone.now()
            post.save()
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/post_edit.html', {'form': form, 'post': post})


# ---------- 편의 기능 2: 감지 기록 아카이브 ----------
# 강의자료 ch08 p3 "DJANGO Blog - 게시판 기능 외 콘텐츠 아카이브 등으로 기능 확장 가능"
# YOLO가 올린 글(제목 = 물체 이름)을 날짜별·물체별로 모아서 보여줌

def archive_days():
    rows = (Post.objects.filter(published_date__lte=timezone.now())
            .annotate(day=TruncDate('published_date'))
            .values('day', 'title')
            .annotate(count=Count('id'))
            .order_by('-day', '-count', 'title'))
    days = []
    for row in rows:
        if not days or days[-1]['date'] != row['day']:
            days.append({'date': row['day'], 'total': 0, 'objects': []})
        days[-1]['total'] += row['count']
        days[-1]['objects'].append({'title': row['title'], 'count': row['count']})
    return days


def post_archive(request):
    return render(request, 'blog/post_archive.html', {'days': archive_days()})


def post_archive_day(request, year, month, day):
    try:
        target = date(year, month, day)
    except ValueError:
        raise Http404('없는 날짜입니다.')
    posts = Post.objects.filter(published_date__lte=timezone.now(), published_date__date=target)
    objects = list(posts.values('title').annotate(count=Count('id')).order_by('-count', 'title'))
    selected = request.GET.get('title', '')
    if selected:
        posts = posts.filter(title=selected)
    return render(request, 'blog/post_archive_day.html', {
        'day': target,
        'objects': objects,
        'total': sum(o['count'] for o in objects),
        'selected': selected,
        'posts': posts.order_by('-published_date'),
    })


def js_test(request):
    return render(request, 'blog/js_test.html', {})


class IntruderImage(viewsets.ModelViewSet):
    # 강의자료 ch08 p12와 같은 이름 (공통평가 01에서는 ch05에 맞춰 BlogImages였음)
    queryset = Post.objects.order_by(F('published_date').desc(nulls_last=True), '-id')
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    def get_queryset(self):
        # 편의 기능 2: 앱에서 날짜·물체를 골라 받을 수 있게 ?date=YYYY-MM-DD, ?title=물체이름 추가
        queryset = super().get_queryset()
        day = self.request.query_params.get('date')
        title = self.request.query_params.get('title')
        if day:
            try:
                queryset = queryset.filter(published_date__date=date.fromisoformat(day))
            except ValueError:
                raise ValidationError({'date': 'YYYY-MM-DD 형식으로 보내야 합니다.'})
        if title:
            queryset = queryset.filter(title=title)
        return queryset

    def perform_create(self, serializer):
        # published_date 없이 올리면 웹 메인 목록에 안 떠서 업로드 시각으로 채움
        published_date = serializer.validated_data.get('published_date') or timezone.now()
        serializer.save(author=self.request.user, published_date=published_date)


class ArchiveSummary(viewsets.ViewSet):
    # 편의 기능 2: 날짜별·물체별 감지 수 (앱의 감지 기록 화면에서 사용)
    def list(self, request):
        days = archive_days()
        for d in days:
            d['date'] = d['date'].isoformat()
        return Response(days)
