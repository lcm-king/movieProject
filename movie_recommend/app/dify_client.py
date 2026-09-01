import httpx
import json
import re
import subprocess
import sys
from .config import DIFY_API_URL, DIFY_API_KEY
from .crud import CANONICAL_GENRES, _normalize_genre


async def call_dify_workflow(workflow_name: str, inputs: dict) -> dict:
    if not DIFY_API_KEY:
        return _mock_response(workflow_name, inputs)

    url = f"{DIFY_API_URL}/workflows/run"

    # Add intent + all possible fields (Dify Start node requires every field)
    payload = {
        "intent": workflow_name,
        "query": "", "movies_info": "",
        "movie_info": "", "question": "",
        "comment_text": "",
        **inputs,
    }

    # Windows: skip httpx (SSL bug with Dify's Cloudflare CDN), go straight to curl
    if sys.platform == "win32":
        return _call_dify_via_curl(url, payload)

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                url,
                json={"inputs": payload, "response_mode": "blocking", "user": "movie-recommend-system"},
                headers={
                    "Authorization": f"Bearer {DIFY_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()
            outputs = data.get("data", {}).get("outputs", {}) or data

            # Normalize output for each workflow type
            if workflow_name == "movie_recommend":
                recs = outputs.get("recommendations") or outputs.get("result") or outputs
                if isinstance(recs, list):
                    return {"recommendations": recs}
                if isinstance(recs, dict) and "recommendations" in recs:
                    return recs
                return {"recommendations": []}
            elif workflow_name == "movie_qa":
                ans = outputs.get("answer") or outputs.get("result") or str(outputs)
                return {"answer": ans}
            elif workflow_name == "sentiment_analysis":
                s = outputs.get("sentiment") or outputs.get("result") or outputs.get("label") or outputs
                if isinstance(s, dict):
                    return s
                return {"sentiment": str(s), "label": ""}
            return outputs
        except Exception as e:
            print(f"Dify API httpx error: {e}")
            # Fallback: try curl (fixes SSL issues on some Windows/Python builds)
            try:
                return _call_dify_via_curl(url, payload)
            except Exception as curl_e:
                print(f"Dify API curl fallback also failed: {curl_e}")
                return _mock_response(workflow_name, inputs)


def _call_dify_via_curl(url: str, payload: dict) -> dict:
    """Fallback Dify API call using curl (bypasses Python SSL issues).

    Writes body to a temp file to avoid MSYS2/Windows UTF-8 mangling with -d.
    """
    import tempfile, os
    body = json.dumps({"inputs": payload, "response_mode": "blocking", "user": "movie-recommend-system"}, ensure_ascii=False)
    tmp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False)
    try:
        tmp.write(body)
        tmp.close()
        cmd = [
            "curl", "-s", "--connect-timeout", "15", "--max-time", "60",
            "-X", "POST", url,
            "-H", f"Authorization: Bearer {DIFY_API_KEY}",
            "-H", "Content-Type: application/json; charset=utf-8",
            "--data-binary", f"@{tmp.name}",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=65)
        if result.returncode != 0:
            raise RuntimeError(f"curl failed (code {result.returncode}): {result.stderr}")
        data = json.loads(result.stdout)
        return data.get("data", {}).get("outputs", {}) or data
    finally:
        os.unlink(tmp.name)


# ── Unified Chat ───────────────────────────────────────────────


async def unified_chat(message: str, movies_data: list = None) -> dict:
    """
    Unified AI chat: local intelligence first, Dify fallback, LLM as last resort.
    Returns {"reply": "...", "source": "local" | "dify" | "llm"}.
    """
    # 1. Try local intent matching (fast, no network)
    local = _try_local_intent(message, movies_data)
    if local:
        return {"reply": local, "source": "local"}

    # 2. Dify general_chat (knowledge base + LLM)
    if DIFY_API_KEY:
        try:
            result = await call_dify_workflow("general_chat", {"query": message})
            reply = result.get("reply") or result.get("answer") or result.get("result") or result.get("output") or ""
            reply = _strip_think_tags(reply)
            if reply and reply != "{}":
                return {"reply": reply, "source": "dify"}
        except Exception:
            pass

    # 3. LLM-powered manual fallback (mock but smarter)
    return {"reply": _mock_general_chat(message, movies_data), "source": "llm"}


def _try_local_intent(message: str, movies_data: list = None) -> str | None:
    """Try to handle the message locally. Returns reply string or None."""
    msg = message.strip()
    ml = msg.lower()

    # ── Greeting ──
    greetings = ["你好", "您好", "嗨", "hello", "hi", "hey", "早上好", "晚上好", "下午好"]
    if any(g in ml for g in greetings):
        return "你好！我是 MovieRec AI 助手，可以帮你推荐电影、回答电影问题、解答各种疑问。有什么我可以帮你的吗？😊"

    # ── Identity / capabilities ──
    if any(w in ml for w in ["你是谁", "你能做什么", "你会什么", "你有什么功能"]):
        return (
            "我是 MovieRec 的 AI 助手！我可以帮你做这些事情：\n\n"
            "🎬 **推荐电影** — 告诉我你喜欢什么类型，我帮你挑选最合适的电影\n"
            "💬 **电影问答** — 问任何关于电影的问题（剧情、评分、演员等）\n"
            "🧠 **通用问答** — 其他问题也可以问我，我会尽力回答\n\n"
            "不用切换功能，直接跟我说就行！"
        )

    # ── Recommendation (must come before sentiment) ──
    rec_keywords = ["推荐", "想看", "找电影", "有没有什么电影", "有什么电影", "看什么", "给我介绍", "介绍几部"]
    is_recommend = any(k in ml for k in rec_keywords)
    genre_mention = [g for g in CANONICAL_GENRES if g in msg] if not is_recommend else []
    has_genre_query = len(genre_mention) > 0 and any(k in ml for k in ["电影", "片", "推荐", "看"])

    if is_recommend or has_genre_query:
        if not movies_data:
            return "我正在加载电影数据，请稍后再试～"
        recs = _mock_recommend_from_list(msg, movies_data)
        if recs:
            lines = [f"🎬 **{r['title']}**\n   {r['reason']}" for r in recs]
            return "根据你的需求，为你推荐以下电影：\n\n" + "\n\n".join(lines)
        return "暂时没找到完全匹配的电影，要不换个描述试试？比如「推荐一部科幻片」或者「想看温馨的爱情电影」～"

    # ── Movie QA (detect movie title in message) ──
    if movies_data:
        title_match = _find_movie_in_message(msg, movies_data)
        if title_match:
            movie = title_match
            qa = _mock_qa_for_movie(msg, movie)
            if qa:
                return qa

    # ── Personal questions (directed at the AI itself) ──
    # Catch these locally before they reach Dify's sentiment code node
    personal_patterns = [
        "你喜欢", "你爱我", "你讨厌", "你觉得我",
        "你在干嘛", "你叫什么", "你多大了",
    ]
    if any(p in ml for p in personal_patterns):
        return "我是 MovieRec 的 AI 助手，一个虚拟程序，没有真实的感情。不过我可以帮你推荐电影、回答电影问题、解答各种疑惑！有什么想聊的吗？😊"

    # Not a local match
    return None


def _mock_recommend_from_list(query: str, movies: list) -> list:
    """Score and return top 3 recommendations (reuses existing scorer)."""
    scored = [(m, _score_movie_for_query(m, query)) for m in movies]
    scored.sort(key=lambda x: x[1], reverse=True)
    scored = [(m, s) for m, s in scored if s > 0]

    mentioned_genres = [g for g in CANONICAL_GENRES if g in query]
    has_explicit_genre = len(mentioned_genres) > 0

    picked = []
    if has_explicit_genre:
        for m, s in scored:
            if len(picked) >= 3:
                break
            mg = m.get("genre", "").split(",")
            if any(g.strip() in mentioned_genres for g in mg):
                picked.append(m)
    else:
        used = set()
        for m, s in scored:
            if len(picked) >= 3:
                break
            top = m.get("genre", "").split(",")[0].strip()
            if top not in used or len(picked) < 2:
                picked.append(m)
                used.add(top)

    if not picked:
        for m in sorted(movies, key=lambda x: x.get("rating", 0), reverse=True)[:3]:
            picked.append(m)

    return [{"title": m["title"], "reason": _generate_reason(m["title"], m.get("genre", ""), m.get("rating", 0), query)} for m in picked]


def _find_movie_in_message(message: str, movies: list) -> dict | None:
    """Check if any known movie title appears in the message."""
    ml = message.lower()
    # Sort by length descending to match longer titles first
    for m in sorted(movies, key=lambda x: -len(x.get("title", ""))):
        t = m.get("title", "").lower()
        if t in ml and len(t) >= 2:
            return m
    return None


def _mock_qa_for_movie(question: str, movie: dict) -> str | None:
    """Answer a question about a specific movie using its data."""
    title = movie.get("title", "")
    genre = movie.get("genre", "")
    year = movie.get("year", "")
    rating = movie.get("rating", 0)
    desc = movie.get("description", "")

    ql = question.lower()

    if any(w in ql for w in ["结局", "结尾", "最后", "结果"]):
        return f"关于《{title}》的结局：{desc[:80]}……这部电影的结局很有深意，建议你亲自观看感受～" if desc else f"《{title}》的结局非常精彩，建议亲自观看体验！"

    if any(w in ql for w in ["意思", "含义", "寓意", "主题", "表达", "传达", "启示", "反映", "想说什么"]):
        return f"《{title}》的主题深刻：{desc[:120]}……影片通过独特的叙事引人深思。" if desc else f"《{title}》是一部值得反复品味的佳作。"

    if any(w in ql for w in ["简介", "内容", "讲什么", "什么故事", "剧情", "关于", "讲什么"]):
        return f"《{title}》（{year}）是一部{genre}类型的电影。{desc}" if desc else f"《{title}》是一部{year}年上映的{genre}类型的电影。"

    if any(w in ql for w in ["评分", "评价", "口碑", "好看吗", "值得", "推荐指数", "几分"]):
        level = "高分经典" if float(rating) >= 8.5 else ("口碑佳作，值得一看" if float(rating) >= 7 else "评价一般，可酌情观看") if rating else ""
        return f"《{title}》评分 **{rating}** 分，属于{level}。类型：{genre}。" if level else f"《{title}》评分**{rating}**分。"

    if any(w in ql for w in ["什么时候", "上映", "年份", "年代", "哪年"]):
        return f"《{title}》于 **{year}** 年上映，是一部{genre}类型的电影。" if year else f"《{title}》是一部{genre}类型的电影。"

    if any(w in ql for w in ["推荐", "类似", "相似", "同类型", "还有", "其他"]):
        return f"喜欢《{title}》的话，可以试试用「{genre.split(',')[0]}」类型在我的电影库中筛选，有很多同类型的好片！也可以告诉我你喜欢什么风格，我帮你推荐～"

    if any(w in ql for w in ["演员", "导演", "主演", "饰演", "阵容", "谁演的", "谁导", "导演是谁"]):
        return f"关于《{title}》的演员和导演信息，当前数据库暂未收录详细演职人员信息，建议在豆瓣或其他影评平台查看～"

    # General info fallback
    return f"**《{title}》**（{year}）｜{genre}｜评分 **{rating}**\n\n{desc[:200]}" if desc else f"**《{title}》**（{year}）｜{genre}｜评分 **{rating}**"


def _mock_general_chat(message: str, movies_data: list = None) -> str:
    """Fallback when neither local intent nor Dify match."""
    msg = message.strip()
    ml = msg.lower()

    # Check if it's about movies in general
    movie_keywords = ["电影", "影片", "导演", "演员", "票房", "奥斯卡", "金鸡", "金马", "戛纳", "好莱坞"]
    if any(k in ml for k in movie_keywords):
        return (
            f"关于「{msg}」这个问题挺有意思的！不过当前本地知识库中还没有足够的信息来详细回答。\n\n"
            "如果你能连接 Dify 并配置好工作流，我可以调用大模型来智能回答这类问题。"
            "现在你可以试试：\n"
            "• 让我推荐电影（如「推荐科幻片」）\n"
            "• 问具体某部电影（如「肖申克的救赎评分多少」）\n"
            "• 分析评论情感（如「这部电影太好看了」）"
        )

    # Completely unrelated question
    return (
        f"关于「{msg}」，我目前的知识库主要涵盖电影相关内容。建议你试试以下功能：\n\n"
        "🎬 **电影推荐** — 告诉我你喜欢什么类型\n"
        "💬 **电影问答** — 问某部电影的具体信息\n"
        "❤️ **情感分析** — 分析你的电影评论\n\n"
         )


def _strip_think_tags(text: str) -> str:
    """Remove 标签（如 Dify LLM 的 <think> 推理过程）."""
    import re as _re
    text = _re.sub(r'<think>.*?</think>', '', text, flags=_re.DOTALL)
    return text.strip()


def _is_valid_uuid(s: str) -> bool:
    return bool(re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', s.strip().lower()))


def _parse_movie_lines(movies_info: str) -> list:
    movies = []
    for line in movies_info.strip().split("\n"):
        line = line.strip()
        if not line.startswith("- "):
            continue
        m = {}
        tm = re.match(r"- (.+?) \((\d{4})\)", line)
        if tm:
            m["title"] = tm.group(1).strip()
            m["year"] = int(tm.group(2))
        gm = re.search(r"类型:\s*(.+?)\s*\|", line)
        if gm:
            m["genre"] = gm.group(1).strip()
        rm = re.search(r"评分:\s*([\d.]+)", line)
        if rm:
            m["rating"] = float(rm.group(1))
        dm = re.search(r"简介:\s*(.+)", line)
        if dm:
            m["description"] = dm.group(1).strip()
        if m.get("title"):
            movies.append(m)
    return movies


def _score_movie_for_query(movie: dict, query: str) -> float:
    score = 0.0
    ql = query.lower()

    if movie.get("title", "").lower() in ql:
        score += 5.0

    for g in movie.get("genre", "").split(","):
        gn = _normalize_genre(g).lower()
        if gn in ql:
            score += 3.0
        for kw in _genre_keywords(gn):
            if kw in ql:
                score += 2.0

    desc = movie.get("description", "").lower()
    overlap = set(desc) & set(ql)
    if overlap:
        score += min(len(overlap) * 0.3, 3.0)

    mood_map = {
        "温馨": ["温暖", "感动", "治愈", "家庭", "成长", "爱"],
        "刺激": ["激烈", "战斗", "冒险", "追逐", "爆炸"],
        "深刻": ["哲理", "反思", "人性", "社会", "意义"],
        "搞笑": ["幽默", "搞笑", "喜剧", "滑稽", "欢笑"],
        "悬疑": ["谜团", "反转", "推理", "悬念", "真相"],
    }
    for mood, kws in mood_map.items():
        if mood in ql:
            for kw in kws:
                if kw in desc:
                    score += 0.5

    score += movie.get("rating", 7.0) * 0.2
    return score


def _genre_keywords(genre: str) -> list:
    return {
        "科幻": ["科幻", "星际", "宇宙", "太空", "外星", "机器人", "未来", "穿越", "时空"],
        "爱情": ["爱情", "恋爱", "浪漫", "感动", "温馨", "情侣", "甜蜜"],
        "动作": ["动作", "打斗", "激烈", "战斗", "冒险", "刺激"],
        "喜剧": ["喜剧", "搞笑", "幽默", "轻松", "欢乐", "开心"],
        "剧情": ["剧情", "故事", "人生", "感人", "深刻", "哲理"],
        "悬疑": ["悬疑", "推理", "烧脑", "反转", "谜题", "真相"],
        "动画": ["动画", "动漫", "卡通", "宫崎骏", "迪士尼"],
        "恐怖": ["恐怖", "惊悚", "吓人", "鬼", "诡异"],
        "犯罪": ["犯罪", "黑帮", "警匪", "卧底", "侦探"],
        "战争": ["战争", "二战", "军事", "战斗", "英雄"],
        "奇幻": ["奇幻", "魔法", "神话", "传说", "仙界"],
    }.get(genre, [genre])


def _generate_reason(title: str, genre: str, rating: float, query: str) -> str:
    g = genre.split(",")[0].strip() if genre else "经典"
    if any(w in query for w in ["温馨", "温暖", "治愈", "感动"]):
        return f"《{title}》是一部温暖人心的{g}片，评分{rating:.1f}分，故事真挚动人。"
    if any(w in query for w in ["刺激", "爽", "燃", "热血", "激烈"]):
        return f"《{title}》节奏紧凑，{g}类型代表，评分{rating:.1f}分，让你肾上腺素飙升。"
    if any(w in query for w in ["搞笑", "轻松", "开心", "喜剧", "欢乐"]):
        return f"《{title}》幽默风趣，{g}类型佳作，评分{rating:.1f}分，让你开怀大笑。"
    if any(w in query for w in ["深刻", "思考", "哲理", "人性", "反思"]):
        return f"《{title}》思想深刻，{g}电影，评分{rating:.1f}分，引人深思。"
    if any(w in query for w in ["悬疑", "烧脑", "推理", "反转"]):
        return f"《{title}》剧情精巧，{g}片悬疑感十足，评分{rating:.1f}分。"
    if any(w in query for w in ["爱情", "恋爱", "情侣", "浪漫", "甜蜜"]):
        return f"《{title}》情感真挚，{g}片评分{rating:.1f}分，令人心动。"
    return f"《{title}》是{g}类型的高分佳作，评分{rating:.1f}分，契合你的需求。"


# ── Mock implementations ───────────────────────────────────────

def _mock_response(workflow_name: str, inputs: dict) -> dict:
    if workflow_name == "movie_recommend":
        query = inputs.get("query", "")
        movies_info = inputs.get("movies_info", "")
        movies = _parse_movie_lines(movies_info)
        if not movies:
            return {"recommendations": []}

        scored = [(m, s) for m in movies if (s := _score_movie_for_query(m, query)) > 0]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Check if user explicitly mentioned a genre in their query
        mentioned_genres = [g for g in CANONICAL_GENRES if g in query]
        has_explicit_genre = len(mentioned_genres) > 0

        picked = []
        if has_explicit_genre:
            # User named a specific genre — prefer only movies of that genre
            for m, s in scored:
                if len(picked) >= 3:
                    break
                movie_genres = m.get("genre", "").split(",")
                if any(g.strip() in mentioned_genres for g in movie_genres):
                    picked.append((m, s))
        else:
            # Vague query — use genre diversity for variety
            used = set()
            for m, s in scored:
                if len(picked) >= 3:
                    break
                top = m.get("genre", "").split(",")[0].strip()
                if top not in used or len(picked) < 2:
                    picked.append((m, s))
                    if len(picked) <= 2:
                        used.add(top)

        if not picked:
            # Explicit genre with no matches — return empty rather than irrelevant results
            if has_explicit_genre:
                return {"recommendations": []}
            # Vague query — fall back to top-rated
            for m in sorted(movies, key=lambda x: x.get("rating", 0), reverse=True)[:3]:
                picked.append((m, 1.0))

        return {
            "recommendations": [
                {"title": m["title"], "reason": _generate_reason(m["title"], m.get("genre", ""), m.get("rating", 0), query)}
                for m, _ in picked
            ]
        }

    if workflow_name == "movie_qa":
        question = inputs.get("question", "")
        movie_info = inputs.get("movie_info", "")

        # Parse actual movie data from movie_info
        tm = re.search(r"标题:\s*(.+?)\n", movie_info)
        title = tm.group(1) if tm else "这部电影"
        gm = re.search(r"类型:\s*(.+?)\n", movie_info)
        genre = gm.group(1) if gm else ""
        ym = re.search(r"年份:\s*(\d+)", movie_info)
        year = ym.group(1) if ym else ""
        rm = re.search(r"评分:\s*([\d.]+)", movie_info)
        rating = rm.group(1) if rm else ""
        dm = re.search(r"简介:\s*(.+)", movie_info)
        desc = dm.group(1).strip() if dm else ""

        # Intelligent matching with actual movie data
        if any(w in question for w in ["结局", "结尾", "最后", "结果"]):
            answer = f"关于《{title}》的结局：{desc[:80]}……这部电影的结局富有深意，建议观影后细细品味。"
        elif any(w in question for w in ["意思", "含义", "寓意", "主题", "表达", "传达", "启示", "反映"]):
            answer = f"《{title}》的主题核心：{desc[:120]}……影片通过独特视角传递了深刻的思想内涵。"
        elif any(w in question for w in ["简介", "内容", "讲什么", "什么故事", "剧情", "关于"]):
            answer = f"《{title}》({year})是一部{genre}类型的电影，豆瓣评分{rating}。{desc}"
        elif any(w in question for w in ["评分", "评价", "口碑", "好看吗", "值得", "推荐指数"]):
            level = "高分佳作，强烈推荐" if float(rating) >= 8 else ("口碑不错，值得一看" if float(rating) >= 6 else "评价一般，可酌情观看") if rating else ""
            answer = f"《{title}》评分{rating}分，属于{level}。类型: {genre}。{desc[:80]}"
        elif any(w in question for w in ["什么时候", "上映", "年份", "年代"]):
            answer = f"《{title}》于{year}年上映，是一部{genre}类型的电影。{desc[:80]}"
        elif any(w in question for w in ["推荐", "类似", "相似", "同类型", "还有"]):
            answer = f"喜欢《{title}》的话，可以在电影库中用「{genre}」类型筛选，找到更多同类型精彩电影。"
        elif any(w in question for w in ["演员", "导演", "主演", "饰演", "阵容", "谁"]):
            answer = f"关于《{title}》的演员阵容，当前数据库暂无详细演职人员信息，建议在电影详情页或其他影评平台查看。"
        else:
            answer = f"《{title}》({year})｜{genre}｜评分{rating}\n简介：{desc[:200]}"

        return {"answer": answer}

    if workflow_name == "general_chat":
        return {"reply": _mock_general_chat(inputs.get("query", ""), _parse_movie_lines(inputs.get("movies_info", "")))}

    if workflow_name == "sentiment_analysis":
        text = inputs.get("comment_text", "")
        pos = ["好看", "精彩", "推荐", "喜欢", "不错", "经典", "感动", "震撼", "完美", "棒",
               "出色", "优秀", "惊艳", "赞", "太棒", "必看", "神作", "杰作", "爱", "享受", "绝佳", "巅峰", "走心"]
        neg = ["烂", "差", "无聊", "失望", "垃圾", "不好看", "浪费", "后悔", "糟糕", "难看",
               "差劲", "尴尬", "拖沓", "空洞", "乏味", "沉闷", "想睡", "不值", "浪费时间", "乱七八糟"]
        pc = sum(1 for w in pos if w in text)
        nc = sum(1 for w in neg if w in text)
        intense = any(w in text for w in ["非常", "太", "极其", "超级", "真的", "绝对", "完全"])
        long_text = len(text) > 30

        if pc > nc:
            sentiment = "正面"
            label = "深度好评" if (pc >= 3 and long_text) else ("极力推荐" if (pc >= 2 and intense) else ("值得一看" if pc >= 2 else "基本满意"))
        elif nc > pc:
            sentiment = "负面"
            label = "强烈吐槽" if (nc >= 3 and intense) else ("不太推荐" if nc >= 2 else "略有遗憾")
        else:
            sentiment = "中性"
            label = "理性评价" if long_text else "中规中矩"
        return {"sentiment": sentiment, "label": label}

    return {}
