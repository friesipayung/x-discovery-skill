# PRD — News-First X.com Seed Account Discovery Skill

## 1. Document Control

- **Product Name:** News-First X Seed Discovery Skill
- **Document Type:** Product Requirements Document (PRD)
- **Primary Use Case:** Menemukan akun X.com yang layak dijadikan seed account untuk crawling berdasarkan isu/topik yang benar-benar sedang dibahas di portal berita dan diposting secara konsisten oleh akun tersebut.
- **Target Runtime:** Claude Code, Opencode, custom agentic tools, workflow runners
- **Persistence:** SQLite
- **AI Dependency:** Menggunakan AI bawaan runtime agentic, bukan evaluator terpisah

---

## 2. Executive Summary

Produk ini adalah **skill agentic** untuk mencari akun X.com yang layak dijadikan **seed data** untuk proses crawling. Skill tidak langsung mencari akun berdasarkan bio atau label topik, tetapi memakai pendekatan **news-first**:

1. cari artikel berita relevan dari portal berita
2. ekstrak keyword, entity, issue phrase, dan istilah penting
3. gunakan keyword tersebut untuk mencari postingan di X.com
4. ekstrak akun dari posting yang benar-benar membahas topik
5. filter akun yang opportunistic atau “riding the waves”
6. gunakan AI bawaan runtime untuk menilai eligibility akun sebagai seed crawl
7. simpan hasil ke SQLite tanpa duplikasi akun

Pendekatan ini bertujuan menghasilkan seed account yang lebih relevan, lebih aktual, dan lebih tahan terhadap noise seperti akun promo, porn, spam, trend hijacking, dan akun yang hanya memanfaatkan isu viral.

---

## 3. Problem Statement

Mencari akun seed untuk crawling X.com secara manual memiliki beberapa masalah:

- pencarian akun berdasarkan bio/profile sering tidak akurat
- akun besar belum tentu benar-benar membahas topik target
- topik yang sedang relevan berubah cepat
- banyak akun yang ikut keyword trending untuk promosi, spam, porn, judi, atau engagement bait
- operator sulit menjaga konsistensi standar seleksi
- rerun mudah menimbulkan data duplikat tanpa sistem persistence yang baik

Kebutuhan utama adalah skill yang bisa menemukan akun yang:

- relevan terhadap topic
- relevan terhadap region
- benar-benar membahas isu pada postingnya
- cukup aktif dan layak dipantau
- bukan akun opportunistic atau spammy
- tersimpan secara konsisten untuk audit dan reuse

---

## 4. Product Vision

Membangun skill discovery modular yang dapat dipakai oleh runtime agentic untuk menghasilkan daftar seed account X.com yang berkualitas tinggi, berdasarkan sinyal berita aktual dan aktivitas posting yang relevan, dengan evaluasi AI dari runtime dan persistence SQLite yang idempotent.

---

## 5. Product Goals

### Primary Goals

- Menemukan akun X.com yang benar-benar membahas topic target.
- Meng-ground pencarian akun dengan keyword dari portal berita.
- Menolak akun yang hanya numpang topik atau trending topic.
- Menyimpan hasil evaluasi ke SQLite tanpa duplicate account master row.
- Mendukung region default `Indonesia` dan override per run.
- Mendukung implementasi sebagai skill yang compatible dengan Claude Code, Opencode, atau orchestrator agent lain.

### Secondary Goals

- Menyediakan audit trail untuk setiap run.
- Mendukung re-evaluation akun dengan prompt atau runtime policy berbeda.
- Memudahkan ekspor hasil eligible untuk pipeline crawling lanjutan.
- Menjaga pipeline tetap deterministic untuk persistence dan dedupe, serta AI hanya dipakai di tahap yang bernilai.

---

## 6. Non-Goals

Fitur berikut di luar scope v1:

- crawling timeline/post secara penuh
- engagement analytics mendalam
- dashboard web production
- user-facing moderation interface
- scheduler distributed multi-node
- graph expansion follower/following
- klasifikasi konten level post yang sangat detail
- deteksi bot tingkat lanjut berbasis histori besar
- implementasi evaluator AI terpisah
- project scaffold Python, `pyproject.toml`, atau skeleton aplikasi

---

## 7. Primary Users

### 7.1 Primary User

- DevOps engineer
- backend engineer
- data engineer
- analyst / monitoring operator
- researcher

Mereka membutuhkan seed account X.com yang layak dipantau untuk topik tertentu.

### 7.2 Secondary User

- Tim monitoring kebijakan publik
- Tim media intelligence
- Tim riset isu politik, pemerintah, pertambangan, ekonomi, influencer, atau niche topic lain

---

## 8. Key Use Cases

1. Operator ingin mencari akun yang membahas **politik Indonesia** dengan minimal 5.000 followers.
2. Operator ingin mencari akun **government / policy** di region `Indonesia` atau override ke `West Java`.
3. Operator ingin mencari akun yang membahas topik **mining policy** berdasarkan keyword yang sedang muncul di berita.
4. Operator ingin memastikan akun promo, porn, judi, atau spam tidak lolos sebagai seed crawl.
5. Operator ingin menjalankan skill yang sama berulang kali tanpa duplikasi account row.
6. Operator ingin menyimpan hasil eligible, rejected, dan uncertain untuk audit.

---

## 9. Core Product Principles

1. **News-grounded discovery** — pencarian harus dimulai dari isu aktual di portal berita.
2. **Post-first relevance** — akun harus dibuktikan melalui posting, bukan bio saja.
3. **Anti-opportunistic** — akun trend hijacker, promo, porn, spam, dan noise harus ditolak.
4. **Deterministic persistence** — penyimpanan dan dedupe tidak boleh bergantung pada AI.
5. **AI for judgment, not for bookkeeping** — AI runtime dipakai untuk relevance judgment dan qualitative scoring, bukan untuk hal yang bisa dilakukan rule-based.
6. **Idempotent reruns** — run yang sama tidak boleh membuat duplicate account master row.
7. **Region-aware by default** — default region adalah `Indonesia`, tetapi dapat dioverride.
8. **Skill-first architecture** — requirement difokuskan pada kontrak skill, bukan implementasi app standalone.

---

## 10. User Stories

1. Sebagai operator, saya ingin memasukkan topik dan minimal followers agar skill bisa mencari kandidat akun yang layak.
2. Sebagai operator, saya ingin skill mengambil keyword dari portal berita agar discovery grounded pada isu aktual.
3. Sebagai operator, saya ingin skill mencari posting X berdasarkan keyword, agar akun yang ditemukan benar-benar membahas topik.
4. Sebagai operator, saya ingin akun spam/promosi/porn/judi/clickbait ditolak otomatis.
5. Sebagai operator, saya ingin AI bawaan runtime menilai eligibility akun dengan alasan yang jelas.
6. Sebagai operator, saya ingin hasil disimpan di SQLite tanpa duplikat akun.
7. Sebagai operator, saya ingin region default `Indonesia`, tapi tetap bisa diganti per run.
8. Sebagai operator, saya ingin bisa ekspor akun `eligible` untuk dipakai pipeline crawling berikutnya.

---

## 11. Product Scope

### In Scope (v1)

- input topic + constraints
- news search dari portal berita
- keyword/entity extraction dari berita
- query expansion untuk pencarian post di X
- search X posts by topic keywords
- account extraction dari matched posts
- deterministic prefilter
- anti riding-the-waves filter
- AI-based account eligibility judgment via runtime
- SQLite persistence
- duplicate prevention
- export hasil eligible
- implementable sebagai skill dengan kontrak input/output jelas

### Out of Scope (v1)

- real-time monitoring
- multi-tenant auth system
- UI approval workflow
- automatic crawl scheduler
- big-data warehouse integration
- ML-based deep behavior detection on all posts
- evaluator AI terpisah sebagai service sendiri
- implementasi app Python lengkap

---

## 12. End-to-End Workflow

```text
operator input
  ↓
search_news_articles
  ↓
extract_topic_keywords_entities
  ↓
build_x_search_queries
  ↓
search_x_posts
  ↓
extract_accounts_from_posts
  ↓
aggregate_topic_signals
  ↓
anti_riding_the_waves_filter
  ↓
deterministic_prefilter
  ↓
ai_judge_eligibility
  ↓
upsert_sqlite
  ↓
summary + export
```

---

## 13. Functional Requirements

### FR-1 — Input Parameters

Skill harus menerima input berikut.

#### Required

- `topic`

#### Optional

- `region` default `Indonesia`
- `min_followers`
- `max_followers`
- `min_posts`
- `language`
- `must_be_verified`
- `must_have_profile_image`
- `include_keywords`
- `exclude_keywords`
- `max_news_articles`
- `max_keywords`
- `max_x_posts`
- `max_accounts_to_evaluate`
- `anti_wave_mode` default `true`
- `save_mode` (`all`, `eligible_only`)
- `custom_prompt_appendix`
- `provider`
- `dry_run`

#### Example Input

```json
{
  "topic": "politics",
  "region": "Indonesia",
  "min_followers": 5000,
  "min_posts": 50,
  "language": "id",
  "must_be_verified": false,
  "max_news_articles": 20,
  "max_keywords": 40,
  "max_x_posts": 300,
  "max_accounts_to_evaluate": 100,
  "anti_wave_mode": true,
  "save_mode": "all"
}
```

### FR-2 — Region Handling

Skill harus mendukung region scope.

Rules:

- jika `region` tidak diisi, default ke `Indonesia`
- `region` harus memengaruhi:
  - query berita
  - keyword extraction context
  - query pencarian post X
  - AI evaluation context
  - metadata yang disimpan ke DB
- region dapat berupa:
  - `Indonesia`
  - `Jakarta`
  - `West Java`
  - `Southeast Asia`
  - `Global`

### FR-3 — News Search

Skill harus mencari artikel dari portal berita yang relevan dengan topic + region.

Minimal output artikel:

- title
- url
- source
- published_at
- snippet
- content excerpt atau body bila tersedia

Rules:

- hasil berita harus diprioritaskan yang paling relevan dan aktual
- artikel tidak relevan harus dieliminasi sebelum keyword extraction bila memungkinkan
- jumlah artikel dibatasi oleh `max_news_articles`

### FR-4 — Keyword and Entity Extraction

Skill harus mengekstrak sinyal berikut dari berita:

- keywords
- named entities
- phrases
- hashtags potensial
- negative keywords

Keyword extraction dapat dilakukan dengan:

- rule-based extraction
- AI runtime extraction
- hybrid

Output harus dapat dipakai untuk query expansion ke X posts.

### FR-5 — X Query Expansion

Skill harus membangun query pencarian post di X dari kombinasi:

- topic
- region
- extracted keywords
- entities
- phrases
- include_keywords
- language hints

Rules:

- query harus cukup beragam untuk mencakup sub-isu
- query tidak boleh terlalu generik hingga memicu noise berlebihan
- query negatif boleh dipakai untuk mengurangi spam bila provider mendukung

### FR-6 — Search X Posts

Skill harus mencari **post** di X berdasarkan keyword/query yang telah dibangun.

Minimal data yang diambil dari setiap post:

- post_id
- text
- created_at
- matched_query
- author_handle
- author_display_name
- author_profile_url
- author_bio
- author_followers_count
- author_following_count bila tersedia
- author_post_count bila tersedia
- author_verified
- author_location_text
- engagement_metrics bila tersedia
- raw_post

Rules:

- discovery kandidat harus berpusat pada post, bukan profile search saja
- post harus dipakai sebagai bukti topical relevance
- jumlah post dibatasi oleh `max_x_posts`

### FR-7 — Account Extraction from Posts

Skill harus mengekstrak akun author dari matched posts dan mengagregasi signal per account.

Minimal signal agregat:

- matched_posts_count
- distinct_keywords_matched
- matched_entities
- sample_posts
- source_queries
- recent_topic_post_count jika bisa dihitung
- anti_wave_flags awal

### FR-8 — Deterministic Prefilter

Skill harus melakukan prefilter rule-based sebelum AI judge.

Kriteria minimal:

- skip jika `followers_count < min_followers`
- skip jika `followers_count > max_followers` bila diisi
- skip jika `post_count < min_posts` bila diisi
- skip jika `must_be_verified = true` dan akun tidak verified
- skip jika keyword terlarang ada di bio/display_name/profile_url
- skip jika region mismatch sangat jelas
- skip duplicate account dalam batch yang sama

### FR-9 — Anti Riding-the-Waves Filter

Skill harus memiliki lapisan filter khusus untuk menolak akun opportunistic atau noise.

Akun yang harus ditolak atau diberi risk tinggi:

- ads/promotional accounts
- affiliate/lead-gen accounts
- porn/NSFW accounts
- gambling/judi/slot/scam accounts
- clickbait farms
- generic trend hijackers
- spam repost farms
- akun yang mencampur topik serius dengan keyword spam tak relevan

#### Strong rejection signals

- bio mengandung keyword terlarang seperti `slot`, `judi`, `casino`, `promo`, `onlyfans`, `bokep`, `open bo`, `pinjol`, `affiliate`
- display_name atau profile_url memuat indikasi kuat spam/promosi/porn
- matched posts terlalu sedikit dan konteksnya opportunistic
- sample posts menunjukkan dominasi noise/promosi daripada topic relevance
- hashtag campur aduk dan tidak konsisten dengan topik

#### Requirement

- anti-wave filter harus bisa berjalan deterministically berbasis rules
- hasil filter harus disertakan ke AI judge sebagai context
- akun yang lolos filter tetap bisa ditolak oleh AI jika dinilai oportunistik

### FR-10 — AI Eligibility Judge

Skill harus memakai AI bawaan runtime agentic untuk menilai apakah akun layak dijadikan seed crawl.

Input ke AI minimal meliputi:

- topic
- region
- operator constraints
- extracted news keywords/entities
- candidate account profile
- aggregated topic signals
- sample matched posts
- anti-wave findings

Output AI harus berupa JSON terstruktur:

```json
{
  "decision": "eligible",
  "score": 90,
  "reason_short": "Akun relevan dan konsisten.",
  "reason_detailed": "Akun menunjukkan keterkaitan kuat dengan topik dan tidak tampak opportunistic.",
  "matched_topic_signals": ["politik", "DPR", "kebijakan"],
  "risk_flags": [],
  "suggested_tags": ["politics", "indonesia", "policy"],
  "opportunistic_score": 8,
  "consistency_score": 84
}
```

Allowed decisions:

- `eligible`
- `not_eligible`
- `uncertain`

### FR-11 — SQLite Persistence

Skill harus menyimpan data ke SQLite dengan idempotent behavior.

Minimal harus menyimpan:

- run metadata
- account master
- account evaluations
- account tags

Opsional tapi direkomendasikan:

- news articles
- run keywords
- account topic signals

### FR-12 — Duplicate Prevention

Duplicate prevention wajib dilakukan dengan aturan:

- lowercase handle
- strip `@`
- normalisasi `x.com/handle` dan `twitter.com/handle`
- trim trailing slash URL
- account master row unik berdasarkan `handle_normalized`
- evaluasi ulang akun harus membuat evaluation row baru, bukan account row baru

### FR-13 — Save Modes

Skill harus mendukung dua mode simpan:

- `all`: simpan semua kandidat yang dievaluasi dan hasilnya
- `eligible_only`: simpan eligible account, tetapi run log dasar masih boleh disimpan

### FR-14 — Export

Skill harus mendukung ekspor akun berdasarkan filter seperti:

- decision = eligible
- topic tertentu
- region tertentu
- score minimum

### FR-15 — Logging and Auditability

Skill harus log:

- run start/end
- jumlah artikel berita
- jumlah keyword hasil extraction
- jumlah post X yang diproses
- jumlah akun hasil agregasi
- jumlah akun terfilter anti-wave
- jumlah akun dievaluasi AI
- jumlah eligible/rejected/uncertain
- error per candidate jika ada

### FR-16 — Runtime Compatibility

Produk harus dapat diimplementasikan sebagai:

- skill dengan `SKILL.md`
- local tool JSON contract
- command runner pada Claude Code, Opencode, atau agentic runtime lain

---

## 14. AI Evaluation Rubric

AI judge harus memakai rubric berikut.

### Eligible

Gunakan jika:

- akun jelas relevan dengan topic
- akun relevan dengan region atau isu nasional/global yang sesuai
- sample posts menunjukkan konsistensi topik
- akun tidak menunjukkan sinyal spam/promosi/porn/gambling/trend hijacking
- akun cukup layak dijadikan seed monitoring

### Uncertain

Gunakan jika:

- ada sinyal relevansi, tapi bukti lemah
- sample posts terlalu sedikit
- metadata kurang lengkap
- akun mungkin relevan, tetapi belum cukup kuat untuk eligible

### Not Eligible

Gunakan jika:

- off-topic
- dominan spam/promosi/porn/gambling/clickbait
- sangat opportunistic
- mismatch region yang jelas
- hanya ikut keyword/topik tanpa kedekatan substantif

AI harus eksplisit diberi instruksi:

- jangan pilih akun hanya karena besar atau verified
- jangan pilih akun hanya karena bio relevan
- sample posts lebih penting daripada bio saja
- opportunistic/trend hijacker harus diberi penalty keras

---

## 15. Data Model

### 15.1 Table: `runs`

Fields:

- `id`
- `started_at`
- `finished_at`
- `topic`
- `region`
- `provider_name`
- `constraints_json`
- `status`
- `total_news_articles`
- `total_keywords`
- `total_x_posts`
- `total_accounts_aggregated`
- `total_prefiltered`
- `total_anti_wave_rejected`
- `total_ai_evaluated`
- `total_eligible`
- `total_not_eligible`
- `total_uncertain`

### 15.2 Table: `news_articles`

Fields:

- `id`
- `run_id`
- `title`
- `url`
- `source`
- `published_at`
- `snippet`
- `content_excerpt`

### 15.3 Table: `run_keywords`

Fields:

- `id`
- `run_id`
- `keyword`
- `keyword_type` (`keyword`, `entity`, `phrase`, `hashtag`, `negative`)

### 15.4 Table: `accounts`

Fields:

- `id`
- `handle`
- `handle_normalized` unique
- `display_name`
- `bio`
- `followers_count`
- `following_count`
- `post_count`
- `verified`
- `profile_url`
- `profile_image_url`
- `location_text`
- `joined_at`
- `primary_region`
- `source_provider`
- `first_seen_at`
- `last_seen_at`
- `raw_profile_json`

### 15.5 Table: `account_topic_signals`

Fields:

- `id`
- `account_id`
- `run_id`
- `matched_posts_count`
- `distinct_keywords_matched`
- `matched_entities_json`
- `sample_posts_json`
- `source_queries_json`
- `anti_wave_flags_json`

### 15.6 Table: `account_evaluations`

Fields:

- `id`
- `run_id`
- `account_id`
- `topic`
- `region`
- `decision`
- `score`
- `reason_short`
- `reason_detailed`
- `matched_topic_signals_json`
- `risk_flags_json`
- `suggested_tags_json`
- `opportunistic_score`
- `consistency_score`
- `runtime_name`
- `prompt_version`
- `created_at`

### 15.7 Table: `account_tags`

Fields:

- `id`
- `account_id`
- `tag`
- unique(`account_id`, `tag`)

---

## 16. Input / Output Contracts

### Input Example

```json
{
  "topic": "government",
  "region": "Indonesia",
  "min_followers": 10000,
  "min_posts": 100,
  "language": "id",
  "must_be_verified": false,
  "max_news_articles": 20,
  "max_keywords": 40,
  "max_x_posts": 300,
  "max_accounts_to_evaluate": 100,
  "anti_wave_mode": true,
  "save_mode": "all",
  "provider": "default",
  "dry_run": false
}
```

### Output Example

```json
{
  "run_id": "20260330T100000Z-abc123",
  "topic": "government",
  "region": "Indonesia",
  "provider": "default",
  "total_news_articles": 16,
  "total_keywords": 28,
  "total_x_posts": 240,
  "total_accounts_aggregated": 97,
  "total_prefiltered": 71,
  "total_anti_wave_rejected": 14,
  "total_ai_evaluated": 57,
  "total_eligible": 21,
  "total_not_eligible": 28,
  "total_uncertain": 8,
  "inserted_accounts": 17,
  "updated_accounts": 40,
  "skipped_duplicates": 25,
  "eligible_accounts": [
    {
      "handle": "example",
      "display_name": "Example",
      "followers_count": 25000,
      "decision": "eligible",
      "score": 89,
      "reason_short": "Akun rutin membahas isu pemerintahan Indonesia."
    }
  ],
  "errors": []
}
```

---

## 17. Quality Requirements

### 17.1 Accuracy

- hasil harus lebih baik daripada profile-only search
- account relevance harus berbasis post evidence
- opportunistic accounts harus berkurang signifikan

### 17.2 Reliability

- failure pada satu candidate tidak boleh menggagalkan keseluruhan run
- failure pada satu article atau satu query X harus tetap memungkinkan partial result

### 17.3 Idempotency

- rerun dengan input serupa tidak menciptakan duplicate account master row

### 17.4 Explainability

- AI result harus punya `reason_short` dan `reason_detailed`
- risk flags harus terekam

### 17.5 Extensibility

- provider berita dan provider X harus pluggable
- prompt judge harus versioned

---

## 18. Error Handling Requirements

Skill harus:

- menangani kegagalan sebagian pada search berita
- menangani output AI yang invalid JSON
- retry langkah AI jika runtime mendukung retry policy
- menangani missing fields pada provider data
- tetap menghasilkan summary parsial bila ada error terbatas
- hanya exit fatal jika persistence atau inisialisasi run gagal total

---

## 19. Security and Configuration

Konfigurasi minimal:

- `SQLITE_PATH`
- `DEFAULT_REGION` default `Indonesia`
- provider credentials sesuai runtime/tooling masing-masing

Rules:

- secret tidak boleh ditulis ke log
- credential management mengikuti runtime agentic yang dipakai
- skill tidak mengasumsikan evaluator API eksternal tersendiri

---

## 20. Suggested Runtime Architecture

Produk direkomendasikan sebagai orchestrator skill dengan sub-tools:

- `search_news_articles`
- `extract_topic_keywords`
- `search_x_posts`
- `aggregate_accounts_from_posts`
- `anti_wave_filter`
- `judge_x_account_seed`
- `upsert_x_seed_account_sqlite`
- `export_seed_accounts`

Skill utama:

- `x_account_seed_discovery`

---

## 21. Suggested Skill Structure

```text
skills/
  x_account_seed_discovery/
    SKILL.md
    prompts/
      seed_judge.md
    schemas/
      input.json
      output.json
    sql/
      schema.sql
    docs/
      PRD.md
      TECHNICAL_DESIGN.md
```

---

## 22. Acceptance Criteria

Produk dianggap memenuhi PRD bila:

 1. operator dapat menjalankan pencarian dengan `topic` dan optional filters
 2. bila `region` kosong, skill memakai `Indonesia`
 3. skill mengambil artikel berita yang relevan lebih dulu
 4. skill mengekstrak keyword/entity dari berita
 5. keyword tersebut dipakai untuk mencari post di X
 6. akun kandidat diekstrak dari matched posts, bukan profile search saja
 7. akun promo/porn/judi/spam/opportunistic dapat difilter oleh anti-wave layer
 8. AI runtime mempertimbangkan profile, matched posts, dan anti-wave findings
 9. hasil eligible / not eligible / uncertain disimpan ke SQLite
10. duplicate account master row tidak terjadi pada rerun
11. summary run menampilkan statistik setiap tahap
12. hasil eligible dapat diekspor untuk pipeline crawling berikutnya

---

## 23. Risks

- kualitas sangat tergantung pada kualitas provider berita dan provider X
- keyword extraction yang buruk dapat menyebabkan query expansion noisy
- keterbatasan search provider X dapat menurunkan coverage
- beberapa akun opportunistic bisa lolos jika sample post terlalu sedikit
- AI judgment bisa drift jika prompt/runtime behavior berubah
- SQLite bisa menjadi bottleneck bila volume sangat besar

---

## 24. Mitigations

- versioning prompt
- simpan sample posts dan risk flags untuk audit
- gunakan deterministic hard-block keywords sebelum AI
- batasi query agar tidak terlalu generik
- simpan evaluasi ulang untuk perbandingan prompt/runtime
- sediakan `dry_run` untuk tuning tanpa DB write penuh

---

## 25. KPIs / Success Metrics

- precision akun `eligible` meningkat dibanding profile-only discovery
- rasio akun spam/opportunistic yang lolos turun signifikan
- duplicate account row = 0 pada rerun normal
- operator time-to-first-seed list menurun
- auditability meningkat dengan tersimpannya alasan evaluasi

---

## 26. Future Enhancements

- human review queue untuk `uncertain`
- scoring berbasis histori lebih panjang
- graph expansion dari seed eligible
- multi-region batch discovery
- provider fusion dari beberapa sumber berita dan sosial
- web UI untuk review hasil
- migrasi ke PostgreSQL untuk multi-user scale

---

## 27. V1 Delivery Definition

V1 dianggap selesai bila:

- workflow news-first → X-post-first → anti-wave → AI judge berjalan end-to-end
- default region `Indonesia` berjalan benar
- region override berjalan benar
- SQLite schema lengkap tersedia
- dedupe akun berdasarkan `handle_normalized` bekerja
- summary hasil run tersedia
- export eligible accounts tersedia
- implementasi dapat dibungkus sebagai skill untuk Claude Code, Opencode, atau runner agentic lain

---

## 28. Recommended Next Deliverables

1. `SKILL.md` final
2. technical design document
3. SQLite schema SQL
4. prompt spec untuk AI judge
5. input/output JSON schema
6. examples penggunaan skill di Claude Code / Opencode