# Reference Library

## Purpose

This file stores curated examples that future drafting sessions should retrieve before writing. It is not a complete archive. It is a compact set of high-signal posts that show how Kristina's voice works in practice.

Use this file together with:

- `docs/00-principles.md`
- `docs/01-current-voice-snapshot.md`
- `docs/04-platform-adaptation.md`
- `docs/12-stop-list.md`
- `docs/13-drafting-recipes.md`

## Retrieval Tags

Each entry uses this structure:

- `platform`: telegram, threads, linkedin
- `post_type`: reaction, field_note, tool_breakdown, opinion, project_update, community, personal, practical_advice, teaser
- `mood`: playful, sharp, curious, practical, lightly_vulnerable, contrarian, proud, lightly_sharp, confident, direct, encouraging, amused, warm, candid, product_minded, transparent
- `depth`: quick, medium, deep
- `topics`: tools, agents, vibe_coding, ai_workflow, career, community, product, personal_brand, engineering_process, codex, claude, gemini, github, learning, cost, infrastructure, ai_review, content_workflow, tone_of_voice, applied_ai, linkedin, personal, setup
- `best_for`: what kind of future draft should retrieve this example
- `watch_out`: what not to over-copy from this example

`platform` and `depth` are closed enums. `post_type`, `mood`, and `topics` are open vocabularies — the values listed above are the active set covered by the seed corpus, and new entries may introduce additional values. All values must be lowercase `snake_case` (no spaces, no hyphens) so that future Step-2 retrieval can match on equality without normalization. When adding a new value, append it to the list above in the same commit that introduces the entry.

When drafting, retrieve 3 to 5 entries that match the topic and format. Do not imitate the examples mechanically. Use them to preserve rhythm, confidence, density, and the human angle.

## Seed Corpus

Seeded from a fresh Telegram export of `@vibecodesh`.

- Export date: 2026-04-28
- Exported posts: 52
- Source date range: 2026-03-22 to 2026-04-27
- Export command: `python3 scripts/export_telegram_posts.py vibecodesh --limit 80 --output /tmp/tov-vibecodesh-step1.jsonl`

## Entries

### REF-TG-034 - Community Field Note

- `platform`: telegram
- `source`: https://t.me/vibecodesh/34
- `published_at`: 2026-03-22
- `post_type`: community, field_note
- `mood`: playful, proud
- `depth`: quick
- `topics`: community, agents, vibe_coding
- `best_for`: short Telegram update after hosting, joining, or nudging a tech community moment
- `watch_out`: keep the pride light; do not turn this into a formal event recap

Representative text:

> Сегодня на ИТ завтрак не просто ходила. Я его и собрала 😜
>
> Обсуждали оркестрацию и подходы к работе с нейронками. Вербовали традиционных программистов в вайбкодеров 😂

Why it matters:

- Opens with a small twist instead of context.
- Makes the author visibly present without over-explaining credentials.
- Lets the joke carry the community-building energy.

### REF-TG-084 - Compact Practice Lesson

- `platform`: telegram
- `source`: https://t.me/vibecodesh/84
- `published_at`: 2026-04-03
- `post_type`: opinion, field_note
- `mood`: practical, lightly_sharp
- `depth`: quick
- `topics`: agents, ai_workflow, engineering_process
- `best_for`: a concise lesson learned from working with agents
- `watch_out`: do not expand it into a tutorial unless the user asks for one

Representative text:

> Кроме шуток. За последнее время не раз убедилась на практике, что в агентской разработке очень важно разделять план и имплементацию.
>
> Иначе будет каша и результат вам скорее всего не понравится ☝️

Why it matters:

- The authority comes from repeated practice, not abstract thought leadership.
- The second paragraph is short, visual, and a little blunt.
- It is a useful default pattern for "one thing I learned this week" posts.

### REF-TG-088 - Multi-Agent Workflow Authority

- `platform`: telegram
- `source`: https://t.me/vibecodesh/88
- `published_at`: 2026-04-04
- `post_type`: tool_breakdown, opinion
- `mood`: confident, practical
- `depth`: medium
- `topics`: agents, ai_workflow, codex, claude, github
- `best_for`: explaining a real workflow or stack without sounding like documentation
- `watch_out`: keep role clarity; avoid turning the author into a passive narrator

Representative text:

> В своей мультиагентной разработке я использую классическую петлю, которую применяют в энтерпрайзе - с обязательным код-ревью. И всё это выполняют агенты: в моём случае Codex и Claude Code.
>
> Моя роль - идея, принятие решений на этапе планирования и финальный мерж по каждой итерации.
>
> Позже расскажу об инструментах, которые использую, и о том, как реализован пайплайн на GitHub.

Why it matters:

- Bridges "serious engineering process" with personal hands-on usage.
- Names the author's role in the loop, which prevents automation from swallowing the human.
- Ends with a natural content-series hook.

### REF-TG-098 - Beginner Advice With Edge

- `platform`: telegram
- `source`: https://t.me/vibecodesh/98
- `published_at`: 2026-04-08
- `post_type`: opinion, practical_advice
- `mood`: direct, encouraging, playful
- `depth`: medium
- `topics`: vibe_coding, learning, community, tools
- `best_for`: "where to start" posts, beginner guidance, debunking over-learning
- `watch_out`: preserve warmth; do not make the take sound dismissive toward beginners

Representative text:

> В последнее время часто встречаю вопрос "С чего начать? Какие курсы посмотреть?". Все гениальное просто 😄 Не нужны вам никакие курсы. Просто начните.
>
> Купите подписку на Claude за 20 долларов, установите claude code по инструкции от него же и погнали. Возьмите для начала какой-нить простенький, тренировочный пет проект (легче начинать с тг-ботов) и на нем тренируйтесь. В процессе разберетесь каких знаний вам не хватает.
>
> Все эти курсы по вайбкодингу устаревают примерно со скоростью света 😅 Потому что буквально каждый день выходит что-то новое. В этом плане намного более продуктивная стратегия объединяться в сообщества.

Why it matters:

- Starts from a question the audience actually asks.
- Makes a strong claim, then grounds it in a concrete first move.
- Keeps the pushy advice friendly through rhythm and emoji.

### REF-TG-102 - Contrarian Tool Take

- `platform`: telegram
- `source`: https://t.me/vibecodesh/102
- `published_at`: 2026-04-09
- `post_type`: reaction, opinion, tool_breakdown
- `mood`: contrarian, practical, amused
- `depth`: medium
- `topics`: tools, claude, agents, cost, infrastructure
- `best_for`: reacting to a hyped launch with a grounded "I tried the adjacent thing" angle
- `watch_out`: do not over-index on negativity; the point is situated judgment

Representative text:

> Пока все обсуждают вчерашнюю новинку от Anthropic - Claude Managed Agents, я не придумала ей применения
>
> Это актуально для тех, кто использует Claude API в своих разработках. И цена кусачая. Стандартная тарификация claude API + $0.08/час 😱
>
> Я ж вам не рассказывала. Но просто ради интереса прикрутила нативное Claude review в GitHub через API Key. За неделю вышло 20 долларов и это мягко говоря не при самой высокой нагрузке. Вернусь, пожалуй, на локальные раннеры и кастомные поделки 😄

Why it matters:

- The hook separates the author's take from the crowd.
- Cost is not abstract; it comes from a real experiment.
- The conclusion has a little shrug, not a manifesto.

### REF-TG-106 - First Project Share

- `platform`: telegram
- `source`: https://t.me/vibecodesh/106
- `published_at`: 2026-04-12
- `post_type`: project_update
- `mood`: lightly_vulnerable, warm, practical
- `depth`: quick
- `topics`: vibe_coding, product, personal
- `best_for`: sharing a shipped experiment, early product, or portfolio artifact
- `watch_out`: keep the vulnerability specific; do not turn it into humblebrag polish

Representative text:

> Первым, что я навайбкодила был онлайн-редактор для создания карты желаний dreamboard
>
> Не судите строго. Ушла буквально неделя. На днях чуть шлифанула мобильную версию, как просили.
>
> С удовольствием послушаю, что еще вы бы улучшили и с помощью каких инструментов? 🤗

Why it matters:

- Makes the artifact real without over-selling it.
- Mentions speed and iteration as lived context.
- Invites feedback in a way that feels human, not engagement-bait.

### REF-TG-120 - Tool Decision Update

- `platform`: telegram
- `source`: https://t.me/vibecodesh/120
- `published_at`: 2026-04-21
- `post_type`: field_note, tool_breakdown
- `mood`: practical, amused, candid
- `depth`: medium
- `topics`: codex, claude, gemini, ai_review, ai_workflow
- `best_for`: explaining why a tool was adopted, dropped, or repositioned
- `watch_out`: preserve the "I tested this" evidence; do not make it sound like a universal benchmark

Representative text:

> В общем, погоняла Gemini на ревью кода пару недель и выключила 😄 Жаль, конечно, 33 бесплатных ревью в день. Но в какой-то момент выяснилось, что она жестко галлюцинирует.
>
> В итоге, пришла к схеме клод - оркестрация и имплементация, кодекс - ревью. Пока что это самая рабочая схема.
>
> Но и тут случаются казусы. Обязательно расскажу об этом попозже.

Why it matters:

- Gives a clear before/after without pretending the decision is final forever.
- Names the practical tradeoff and the updated stack.
- Uses "пока что" to keep authority adaptive.

### REF-TG-129 - Product Meta In The Author's Voice

- `platform`: telegram
- `source`: https://t.me/vibecodesh/129
- `published_at`: 2026-04-25
- `post_type`: project_update, personal
- `mood`: playful, candid, product_minded
- `depth`: medium
- `topics`: product, tone_of_voice, agents, content_workflow
- `best_for`: explaining this repository/product without sounding like generic SaaS positioning
- `watch_out`: keep the "not AI slop" distinction sharp; avoid corporate product language

Representative text:

> В моем поле сейчас очень много интересного в сфере ии попадается. Но я просто на успеваю вам все приносить. Не хватает 25-го часа в сутках 😂
>
> Сейчас пилю бота, который должен мне с этим помочь. Не ии слоп писать, а именно подстраиваться под my tone of voice. И со временем самосовершенствоваться. Там будет ~~с блекджеком и~~ со встроенным скорингом. Посмотрим, что из этого выйдет 🤷‍♀️ Если выйдет хорошо, сделаю репку публичной.

Why it matters:

- This is the product premise in native voice.
- It names the anti-goal directly: not AI slop.
- The ambition is softened by experiment framing.

### REF-TG-134 - Setup Cost Breakdown

- `platform`: telegram
- `source`: https://t.me/vibecodesh/134
- `published_at`: 2026-04-27
- `post_type`: tool_breakdown
- `mood`: transparent, playful, practical
- `depth`: medium
- `topics`: agents, ai_workflow, cost, setup
- `best_for`: posts that make a stack, budget, or workflow legible
- `watch_out`: keep the numbers anchored; do not add generic ROI framing; do not lift the "$124 total" line as an authoritative cost benchmark — it is the author's verbatim self-summary, not an arithmetic sum (see "Note on cost figures" below)

Representative text:

> Так-с, обещала вам рассказать во сколько обходится мой текущий сетап мультиагентной разработки
>
> Итак:
> - Chat GPT 20 долларов
> - Claude 100 долларов
> - GitHub 4 доллара
> - Anthropic API примерно 20 долларов в месяц (для всяких там личных обработчиков типа тг-ботов и прочего)
> - AWS пока использую бесплатный триал на 6 месяцев
>
> Итого, примерно 124 доллара в месяц 💸 И бонусная фоточка, подтверждающая, что этот канал пока не захватили ии 😜

Note on cost figures:

- The quoted total ("примерно 124 доллара") is the author's rounded self-summary, kept verbatim because the reference library preserves source text. The itemized list (20 + 100 + 4 + ~20) actually sums to ≈$144 per month excluding the free AWS trial. Treat $124 as voice/style memory only; any draft that needs an accurate cost number must recompute from the line items rather than quote the total.

Why it matters:

- Useful information is packaged with personality.
- The list stays concrete and short.
- The ending protects the channel from becoming faceless tooling content.

### REF-TG-137 - Teaser From Research

- `platform`: telegram
- `source`: https://t.me/vibecodesh/137
- `published_at`: 2026-04-27
- `post_type`: field_note, teaser
- `mood`: amused, sharp, curious
- `depth`: quick
- `topics`: career, applied_ai, linkedin, personal_brand
- `best_for`: teasing a coming series after research or exploration
- `watch_out`: do not over-explain the full argument; leave some pull for the next post

Representative text:

> И вот вчера сижу, решила глянуть, а что там у других Applied AI Engineers написано. И накопала много интересного 😄
>
> Короче, запилю на днях пару постов об этом. Для затравочки, например, что меня удивило, кто-то еще пишет прямо в тайтле RAG, LangChain, n8n. Да разверзнуться врата в ад 😏

Why it matters:

- Starts in first-person motion.
- Makes the upcoming topic feel alive before the analysis lands.
- The final line has a strong comic snap and clear opinion.

## Retrieval Shortcuts

Use these shortcuts when drafting:

- `quick_telegram_reaction`: REF-TG-084, REF-TG-120, REF-TG-137
- `tool_or_setup_breakdown`: REF-TG-088, REF-TG-102, REF-TG-134
- `project_update`: REF-TG-106, REF-TG-129
- `community_or_event`: REF-TG-034, REF-TG-098
- `contrarian_take`: REF-TG-102, REF-TG-120, REF-TG-137
