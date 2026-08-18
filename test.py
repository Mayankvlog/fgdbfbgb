from fake_useragent import UserAgent


ua = UserAgent(
    browsers=["Edge", "Safari", "Chrome"],
    platforms=["desktop"],
    fallback="a",
)

print(ua.random)
