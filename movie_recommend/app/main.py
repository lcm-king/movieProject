import random
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import engine, Base, SessionLocal
from .models import Movie, User, Genre, MovieGenre
from .routers import users, movies, ratings, comments, recommendations, ai, admin
from .crud import seed_genres, CANONICAL_GENRES, _normalize_genre

app = FastAPI(title="电影推荐与评价系统", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(users.router)
app.include_router(movies.router)
app.include_router(ratings.router)
app.include_router(comments.router)
app.include_router(recommendations.router)
app.include_router(ai.router)
app.include_router(admin.router)

# Static
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "电影推荐系统运行正常"}


# ═══════════════════════════════════════════════════════════════
# Seed data
# ═══════════════════════════════════════════════════════════════

SEED_MOVIES = [
    {"title": "肖申克的救赎", "description": "银行家安迪因被误判杀害妻子及其情人而入狱，在肖申克监狱中经历了种种磨难，最终凭借智慧和毅力重获自由。讲述了一个关于希望、友谊和救赎的动人故事。", "genres": ["剧情", "犯罪"], "cover_url": "https://picsum.photos/seed/movie1/400/600", "release_year": 1994},
    {"title": "霸王别姬", "description": "段小楼与程蝶衣从小在京剧班学艺，两人合演《霸王别姬》成名。历经半个世纪的悲欢离合，演绎了一段荡气回肠的情感故事。", "genres": ["剧情", "爱情", "历史"], "cover_url": "https://picsum.photos/seed/movie2/400/600", "release_year": 1993},
    {"title": "阿甘正传", "description": "智商只有75的阿甘，凭借着自己的执着和纯真，经历了美国几十年的重大历史事件，创造了一个又一个奇迹。", "genres": ["剧情", "喜剧", "爱情"], "cover_url": "https://picsum.photos/seed/movie3/400/600", "release_year": 1994},
    {"title": "星际穿越", "description": "未来地球面临粮食危机，前NASA宇航员库珀被选中穿越虫洞，前往另一个星系寻找人类新家园。一部融合了科学与情感的壮丽史诗。", "genres": ["科幻", "冒险", "剧情"], "cover_url": "https://picsum.photos/seed/movie4/400/600", "release_year": 2014},
    {"title": "盗梦空间", "description": "专业窃贼柯布能在人们梦境中窃取秘密，为回到孩子身边，他接受了一项看似不可能的任务——在目标人物的潜意识中植入一个想法。", "genres": ["科幻", "动作", "悬疑"], "cover_url": "https://picsum.photos/seed/movie5/400/600", "release_year": 2010},
    {"title": "泰坦尼克号", "description": "1912年泰坦尼克号首航，穷画家杰克与贵族少女罗丝在船上相遇相恋，却遭遇了人类历史上最大的海难之一。", "genres": ["爱情", "灾难", "剧情"], "cover_url": "https://picsum.photos/seed/movie6/400/600", "release_year": 1997},
    {"title": "千与千寻", "description": "10岁少女千寻随父母搬家途中误入神灵世界，父母因贪吃变成了猪，千寻必须在这个奇幻世界中工作生存，寻找解救父母的办法。", "genres": ["动画", "奇幻", "冒险"], "cover_url": "https://picsum.photos/seed/movie7/400/600", "release_year": 2001},
    {"title": "教父", "description": "黑手党柯里昂家族的故事。维托·柯里昂是纽约最有权势的黑帮首领，他的小儿子迈克尔从不愿涉足家族事务，到最终成为新一代教父。", "genres": ["犯罪", "剧情"], "cover_url": "https://picsum.photos/seed/movie8/400/600", "release_year": 1972},
    {"title": "蝙蝠侠：黑暗骑士", "description": "蝙蝠侠面对有史以来最疯狂的对手——小丑。小丑制造了一系列混乱，企图让哥谭市陷入无序，蝙蝠侠必须在规则与正义之间做出选择。", "genres": ["动作", "犯罪", "剧情"], "cover_url": "https://picsum.photos/seed/movie9/400/600", "release_year": 2008},
    {"title": "美丽人生", "description": "犹太青年圭多用幽默和想象力在纳粹集中营中保护儿子的幼小心灵，让残酷的现实变成了一场游戏。", "genres": ["剧情", "喜剧", "战争"], "cover_url": "https://picsum.photos/seed/movie10/400/600", "release_year": 1997},
    {"title": "怦然心动", "description": "从二年级开始，朱莉就喜欢上了邻居布莱斯。随着岁月流逝，两人的关系经历了微妙的变化，这是一个关于成长和初恋的温暖故事。", "genres": ["爱情", "剧情", "家庭"], "cover_url": "https://picsum.photos/seed/movie11/400/600", "release_year": 2010},
    {"title": "楚门的世界", "description": "楚门从出生起就生活在由一个巨大的摄影棚构建的世界中，他的一切都是被安排好的真人秀。当他发现真相后，必须决定是否走出这个虚假的世界。", "genres": ["剧情", "喜剧", "科幻"], "cover_url": "https://picsum.photos/seed/movie12/400/600", "release_year": 1998},
    {"title": "功夫", "description": "小混混阿星误闯猪笼城寨，意外卷入了斧头帮与隐世高手之间的对决。一部集武打、搞笑、特效于一体的周星驰经典之作。", "genres": ["动作", "喜剧", "奇幻"], "cover_url": "https://picsum.photos/seed/movie13/400/600", "release_year": 2004},
    {"title": "辛德勒的名单", "description": "二战期间，德国商人辛德勒目睹纳粹对犹太人的残酷迫害后，倾尽家财拯救了1100多名犹太人的生命。", "genres": ["剧情", "历史", "战争"], "cover_url": "https://picsum.photos/seed/movie14/400/600", "release_year": 1993},
    {"title": "机器人总动员", "description": "地球被垃圾覆盖，孤独的清扫机器人瓦力在日复一日的工作中，遇到了来自外太空的搜索机器人伊芙，一段跨越银河的爱情故事就此展开。", "genres": ["动画", "科幻", "冒险"], "cover_url": "https://picsum.photos/seed/movie15/400/600", "release_year": 2008},
    {"title": "无间道", "description": "警方卧底陈永仁与黑帮卧底刘建明分别潜入对方组织，两人在身份错位中展开了一场紧张的对决，都想找出对方的真实身份。", "genres": ["犯罪", "悬疑", "剧情"], "cover_url": "https://picsum.photos/seed/movie16/400/600", "release_year": 2002},
    {"title": "疯狂动物城", "description": "兔子朱迪成为动物城第一位兔警官，与狡猾的狐狸尼克搭档，揭开了一桩动物失踪案背后的阴谋。", "genres": ["动画", "冒险", "喜剧"], "cover_url": "https://picsum.photos/seed/movie17/400/600", "release_year": 2016},
    {"title": "海上钢琴师", "description": "1900年，一个被遗弃在豪华邮轮上的婴儿成长为一位钢琴天才。他一生从未踏上陆地，用音乐诠释着对世界的理解。", "genres": ["剧情", "音乐", "爱情"], "cover_url": "https://picsum.photos/seed/movie18/400/600", "release_year": 1998},
    {"title": "大话西游", "description": "至尊宝为了救紫霞仙子穿越时空，在荒诞的旅途中逐渐领悟了爱情的真谛。一部集喜剧与悲剧于一体的经典之作。", "genres": ["喜剧", "奇幻", "爱情"], "cover_url": "https://picsum.photos/seed/movie19/400/600", "release_year": 1995},
    {"title": "放牛班的春天", "description": "落魄音乐家克莱芒来到一所名为'池塘之底'的男子寄宿学校担任代课教师，用音乐感化了一群问题少年。", "genres": ["剧情", "音乐"], "cover_url": "https://picsum.photos/seed/movie20/400/600", "release_year": 2004},
    {"title": "黑客帝国", "description": "黑客尼奥发现看似正常的现实世界实际上是由一个名为'矩阵'的计算机人工智能系统控制的虚拟世界。他加入了反抗组织，开始对抗矩阵。", "genres": ["科幻", "动作"], "cover_url": "https://picsum.photos/seed/movie21/400/600", "release_year": 1999},
    {"title": "飞屋环游记", "description": "78岁的老人卡尔用成千上万个气球将自己的房子升上天空，前往南美探险。意外带上8岁的小男孩罗素，两人经历了一段难忘的冒险。", "genres": ["动画", "冒险", "剧情"], "cover_url": "https://picsum.photos/seed/movie22/400/600", "release_year": 2009},
    {"title": "致命魔术", "description": "19世纪末的伦敦，两位魔术师为争夺观众和行业顶尖地位展开了长期而残酷的竞争，彼此不惜一切代价互相拆台和超越。", "genres": ["悬疑", "剧情", "科幻"], "cover_url": "https://picsum.photos/seed/movie23/400/600", "release_year": 2006},
    {"title": "你的名字。", "description": "生活在乡下的三叶和东京男孩泷在某天早晨醒来发现彼此互换了身体。穿越时空的奇妙缘分，编织出一段感人至深的故事。", "genres": ["动画", "爱情", "奇幻"], "cover_url": "https://picsum.photos/seed/movie24/400/600", "release_year": 2016},
    {"title": "复仇者联盟", "description": "神盾局长尼克·弗瑞集结钢铁侠、美国队长、雷神、绿巨人、黑寡妇和鹰眼，组成了超级英雄团队'复仇者联盟'，共同对抗外星入侵者。", "genres": ["动作", "科幻", "冒险"], "cover_url": "https://picsum.photos/seed/movie25/400/600", "release_year": 2012},
]

SEED_USERS = [
    {"username": "testuser", "email": "test@movie.com", "password": "test123", "role": "user", "preferred_genres": "剧情,爱情,动画"},
]


@app.on_event("startup")
def startup_event():
    # Only drop/recreate if schema changed (check if genres table exists)
    from sqlalchemy import inspect
    inspector = inspect(engine)
    needs_rebuild = "genres" not in inspector.get_table_names()

    if needs_rebuild:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Seed canonical genres
        seed_genres(db)

        # Build name→id lookup
        genre_map = {g.name: g.id for g in db.query(Genre).all()}

        # 2. Seed movies + movie_genre links
        if db.query(Movie).count() == 0:
            for m in SEED_MOVIES:
                genre_str = ",".join(m["genres"])
                avg = round(random.uniform(6.0, 9.8), 1)
                cnt = random.randint(50, 5000)
                movie = Movie(
                    title=m["title"],
                    description=m["description"],
                    genre=genre_str,
                    cover_url=m["cover_url"],
                    release_year=m["release_year"],
                    avg_rating=avg,
                    rating_count=cnt,
                )
                db.add(movie)
                db.flush()  # get movie.id

                # Link genres via junction table
                for g_name in m["genres"]:
                    g_id = genre_map.get(_normalize_genre(g_name))
                    if g_id:
                        db.add(MovieGenre(movie_id=movie.id, genre_id=g_id))

            db.commit()
            print("Seed: 25 movies + genre links inserted")

        # 3. Seed users
        if db.query(User).count() == 0:
            from .auth import hash_password as hp
            for u in SEED_USERS:
                user = User(
                    username=u["username"],
                    email=u["email"],
                    hashed_password=hp(u["password"]),
                    preferred_genres=u["preferred_genres"],
                    role=u["role"],
                    is_active=True,
                )
                db.add(user)
            db.commit()
            print("Seed: admin/admin123, testuser/test123 inserted")

    finally:
        db.close()

    # ── Migration: demote default seed admin if real users exist ──
    db = SessionLocal()
    try:
        seed_admin = db.query(User).filter(User.username == "admin", User.role == "admin").first()
        real_user_count = db.query(User).filter(~User.username.in_(["admin", "testuser"])).count()
        if seed_admin and real_user_count > 0:
            seed_admin.role = "user"
            db.commit()
            print(f"Migration: demoted seed 'admin' to regular user ({real_user_count} real users exist)")
    finally:
        db.close()
