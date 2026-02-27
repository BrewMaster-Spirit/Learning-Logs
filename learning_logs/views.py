import os
from openai import OpenAI
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import Http404

from .models import Topic, Entry
from .forms import TopicForm, EntryForm

def index(request):
    """学习笔记的主页。"""
    return render(request, 'learning_logs/index.html')

@login_required
def topics(request):
    """显示所有的主题。"""
    topics = Topic.objects.filter(owner=request.user).order_by('date_added')
    context = {'topics': topics}
    return render(request, 'learning_logs/topics.html', context)

@login_required
def topic(request, topic_id):
    """显示单个主题及其所有的条目。"""
    topic = Topic.objects.get(id=topic_id)
    if topic.owner != request.user:
        raise Http404
    entries = topic.entry_set.order_by('-date_added')
    context = {'topic': topic, 'entries': entries}
    return render(request, 'learning_logs/topic.html', context)

@login_required
def new_topic(request):
    """添加新主题。"""
    if request.method != 'POST':
        # 未提交数据：创建一个新表单。
        form = TopicForm()
    else:
        # POST提交的数据：对数据进行处理。
        form = TopicForm(data=request.POST)
        if form.is_valid():
            new_topic = form.save(commit=False)
            new_topic.owner = request.user
            new_topic.save()
            return redirect('learning_logs:topics')
    # 显示空表单或指出表单数据无效。
    context = {'form': form}
    return render(request, 'learning_logs/new_topic.html', context)

@login_required
def new_entry(request, topic_id):
    topic = Topic.objects.get(id=topic_id)
    if request.method != 'POST':
        # 未提交数据：创建一个空表单。
        form = EntryForm()
    else:
        # POST提交的数据：对数据进行处理。
        form = EntryForm(data=request.POST)
        if form.is_valid():
            new_entry = form.save(commit=False)
            new_entry.topic = topic
            new_entry.save()
            return redirect('learning_logs:topic', topic_id=topic_id)
    # 显示空表单或指出表单数据无效。
    context = {'topic': topic, 'form': form}
    return render(request, 'learning_logs/new_entry.html', context)

@login_required
def edit_entry(request, entry_id):
    entry = Entry.objects.get(id=entry_id)
    topic = entry.topic
    if topic.owner != request.user:
        raise Http404

    if request.method != 'POST':
        # 初次请求：使用当前条目填充表单。
        form = EntryForm(instance=entry)
    else:
        # POST提交的数据：对数据进行处理。
        form = EntryForm(instance=entry, data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('learning_logs:topic', topic_id=topic.id)
    context = {'entry': entry, 'topic': topic, 'form': form}
    return render(request, 'learning_logs/edit_entry.html', context)

@login_required
def ai_analysis(request):
    """用AI分析所有笔记，总结要点、生成复习题、发现知识关联。"""
    topics = Topic.objects.filter(owner=request.user).order_by('date_added')
    
    # 整理所有笔记内容
    all_notes = ""
    for t in topics:
        entries = t.entry_set.order_by('-date_added')
        if entries:
            all_notes += f"\n\n【主题：{t.text}】\n"
            for e in entries:
                all_notes += f"- {e.text}\n"
    
    analysis = None
    error = None
    
    if request.method == 'POST':
        if not all_notes.strip():
            error = "你还没有任何笔记，请先添加一些笔记再进行分析。"
        else:
            try:
                client = OpenAI(
                    api_key=os.environ.get('DEEPSEEK_API_KEY'),
                    base_url="https://api.deepseek.com"
                )
                prompt = f"""请分析以下学习笔记，并提供：

1. 📌 各主题要点总结（每个主题用3-5句话概括核心内容）
2. 🔗 知识点关联分析（找出不同主题之间的联系和共同概念）
3. ❓ 复习题（针对重要知识点生成5-8道问题，帮助巩固记忆）

笔记内容如下：
{all_notes}

请用中文回答，格式清晰易读。"""

                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                )
                analysis = response.choices[0].message.content
            except Exception as e:
                error = f"AI分析出错：{str(e)}"
    
    context = {
        'topics': topics,
        'analysis': analysis,
        'error': error,
    }
    return render(request, 'learning_logs/ai_analysis.html', context)