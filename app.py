import streamlit as st
from streamlit.components.v1 import iframe
import random
import dateparser
import datetime
import pandas as pd
import altair as alt
from zipfile import ZipFile
from bs4 import BeautifulSoup


st.set_page_config("Stacklyzer", "📚", "wide")

st.header("Stacklyzer - Simple stats for your Substack!")

st.markdown(
    """
This app will help you understand your Substack publication a bit better.
To begin, go to your Settings, navigate to the Exports section, and create a new data export.
Once that is ready, download it, and upload it in the sidebar file input.
We'll take care of the rest.
"""
)

st.info(
    """
Stacklyzer is a 100%% free and [open source software](https://github.com/apiad/stacklyzer).
If you want to contribute with its development, you can either [consider making a donation](https://tppay.me/lpsx71j6), or [subscribe to my free blog](https://blog.apiad.net/subscribe).
""",
    icon="💖",
)

data_fp = st.sidebar.file_uploader("Upload your Substack data dump here.", type="zip")

if not data_fp:
    st.warning("Upload your data to continue.", icon="🔥")
    st.stop()

data = ZipFile(data_fp)
files = data.filelist
html_files = [f for f in data.filelist if f.orig_filename.endswith(".html")]


@st.cache_data
def parse_texts(filename):
    progress = st.sidebar.progress(0, "Parsing posts...")

    texts = {}

    for i, file in enumerate(html_files):
        progress.progress(
            (i + 1) / len(html_files), f"Parsing posts ({i+1}/{len(html_files)})"
        )

        with data.open(file) as fp:
            soup = BeautifulSoup(fp.read(), "html")
            texts[file] = soup.get_text()

    progress.empty()

    return texts


deliver_files = [f for f in data.filelist if f.filename.endswith("delivers.csv")]


@st.cache_data
def parse_delivers(filename):
    progress = st.sidebar.progress(0, "Parsing delivers...")

    dfs = []

    for i, file in enumerate(deliver_files):
        progress.progress(
            (i + 1) / len(deliver_files),
            f"Parsing delivers ({i+1}/{len(deliver_files)})",
        )

        with data.open(file) as fp:
            dfs.append(pd.read_csv(fp))

    progress.empty()

    return pd.concat(dfs, ignore_index=True)


open_files = [f for f in data.filelist if f.filename.endswith("opens.csv")]


@st.cache_data
def parse_opens(filename):
    progress = st.sidebar.progress(0, "Parsing opens...")

    dfs = []

    for i, file in enumerate(open_files):
        progress.progress(
            (i + 1) / len(open_files), f"Parsing opens ({i+1}/{len(open_files)})"
        )

        with data.open(file) as fp:
            dfs.append(pd.read_csv(fp))

    progress.empty()

    return pd.concat(dfs, ignore_index=True)


texts = parse_texts(data.filename)
delivers = parse_delivers(data.filename)
opens = parse_opens(data.filename)


## QUICKINFO

st.subheader("⭐ Quick info", divider="rainbow")

cols = st.columns(5)
metric_sub = cols[0].metric("🧑‍🤝‍🧑 Total subscribers", 0)
metric_paid = cols[1].metric("💰 Paid subscribers", 0)
metric_emails = cols[2].metric("📧 Emails sent", 0)
metric_gar = cols[3].metric("💲 Current GAR", 0)
target_gar = cols[4].metric("📆 Days to target GAR", 0)


## SUBS

st.subheader("🧑‍🤝‍🧑 Subscribers", divider="orange")

email_list = [f for f in files if f.orig_filename.startswith("email_list")][0]

with data.open(email_list) as fp:
    subs_df = pd.read_csv(fp)

total = len(subs_df)
yearly = len(subs_df[subs_df["plan"] == "yearly"])
monthly = len(subs_df[subs_df["plan"] == "monthly"])
paid = yearly + monthly
comp = len(subs_df[subs_df["plan"] == "comp"])
start_date: datetime.datetime = dateparser.parse(subs_df["created_at"].min())
end_date: datetime.datetime = dateparser.parse(subs_df["created_at"].max())
three_month = end_date - datetime.timedelta(days=90)
weeks = (end_date - start_date).days / 7
avg = len(subs_df) / weeks

subs90 = len(subs_df[subs_df["created_at"] >= str(three_month)]) / 90

metric_sub.metric("🧑‍🤝‍🧑 Total subscribers", len(subs_df), delta=round(avg, 1))
metric_paid.metric("💰 Paid subscribers", paid)

st.info(
    f"You have **{len(subs_df)}** active subscribers, including **{paid} paid** and **{comp} active comps**, averaging **{avg:.1f}** new subscribers per week.",
    icon="🧑‍🤝‍🧑",
)

subscribers = subs_df.groupby(["created_at"]).count().reset_index()
subscribers["total"] = subscribers["email"].cumsum()

left, mid, right = st.columns([3, 2, 1.5])

with left:
    st.altair_chart(
        alt.Chart(subscribers)
        .mark_line()
        .encode(
            x=alt.X("created_at:T", title="Subscription date"),
            y=alt.Y("total", title="Total subscribers"),
        ),
        use_container_width=True,
    )

with mid:
    st.altair_chart(
        alt.Chart(subs_df)
        .mark_bar()
        .encode(
            x=alt.X("week(created_at):T", title="Week"),
            y=alt.Y("count(email)", title="Subscribers per week"),
        ),
        use_container_width=True,
    )

with right:
    st.altair_chart(
        alt.Chart(subs_df).mark_arc().encode(theta="count(email)", color="plan"),
        use_container_width=True,
    )

with st.expander("Raw subscriber data"):
    st.dataframe(subs_df, use_container_width=True)


## EMAILS

st.subheader("📧 Emails", divider="blue")

with data.open("posts.csv") as fp:
    posts_df = pd.read_csv(fp)

posts_df["raw_id"] = pd.to_numeric(
    posts_df["post_id"].str.split(".", n=1, expand=True)[0]
)

published = posts_df[posts_df["email_sent_at"].notnull()]
start_date: datetime.datetime = dateparser.parse(published["email_sent_at"].min())
end_date: datetime.datetime = dateparser.parse(published["email_sent_at"].max())
weeks = (end_date - start_date).days / 7
avg = len(published) / weeks
newsletters = len(published[published["type"] == "newsletter"])

metric_emails.metric(
    "📧 Emails sent", len(published), delta=round(avg, 1), delta_color="off"
)

st.info(
    f"💌 So far you've sent **{len(published)}** emails, averaging **{avg:.1f} posts per week**. Of these, **{newsletters}** are original newsletter posts."
)

left, mid, right = st.columns([3, 2, 1.5])

with left:
    st.altair_chart(
        alt.Chart(published)
        .mark_bar()
        .encode(
            x=alt.X("week(email_sent_at):T", title="Date"),
            y=alt.Y("count(title)", title="Posts sent per week"),
            color=alt.Color("type", title="Type", legend=None),
        ),
        use_container_width=True,
    )

with mid:
    st.altair_chart(
        alt.Chart(published)
        .mark_bar()
        .encode(
            x=alt.X("month(email_sent_at):T", title="Date"),
            y=alt.Y("count(title)", title="Posts sent per month"),
            color=alt.Color("type", title="Type", legend=None),
        ),
        use_container_width=True,
    )

with right:
    st.altair_chart(
        alt.Chart(published).mark_arc().encode(theta="count(title)", color="type"),
        use_container_width=True,
    )


with st.expander("Raw posts data"):
    st.write("#### Posts")
    st.dataframe(posts_df)

    st.write("#### Delivers")
    st.dataframe(delivers)

    st.write("#### Opens")
    st.dataframe(opens)


st.write("#### How much are your subscribers reading?")


@st.cache_data
def compute_unique_opens(filename):
    return opens.groupby(["post_id", "email"]).agg(timestamp=("timestamp", "min"))


unique_opens = compute_unique_opens(data.filename)
total_opens = len(unique_opens)
open_rate = total_opens / len(delivers)


@st.cache_data
def compute_open_rates(filename):
    deliver_totals = delivers.groupby("post_id").agg(
        delivers=("email", "count"), when=("timestamp", "min")
    )
    open_totals = (
        opens.groupby(["post_id", "email"])
        .count()
        .reset_index()
        .groupby("post_id")
        .agg(opens=("email", "count"))
    )
    totals = deliver_totals.join(open_totals).join(
        posts_df[["raw_id", "title", "type"]].set_index("raw_id")
    )
    totals["rate"] = totals["opens"] / totals["delivers"]

    return totals.reset_index()


open_rates = compute_open_rates(data.filename)


st.info(
    f"You have sent a total of {len(delivers)} emails and received a total of {total_opens} unique opens ({open_rate*100:.2f}% open rate).",
    icon="💌",
)


@st.cache_data
def compute_subscriber_behavior(filename):
    deliver_totals = delivers.groupby("email").agg(delivers=("post_id", "count"))
    open_totals = opens.groupby("email").agg(opens=("post_id", "count"))
    totals = (
        deliver_totals.join(open_totals)
        .join(subs_df.set_index("email"), how="outer")
        .reset_index()
    )
    totals["active"] = totals["email"].isin(subs_df["email"])
    totals.loc[totals["opens"].isnull(), "opens"] = 0
    totals.loc[totals["delivers"].isnull(), "delivers"] = 0

    return totals.reset_index()


subs_behavior = compute_subscriber_behavior(data.filename)

total_subs_ever = len(subs_behavior[subs_behavior["delivers"] > 0])
total_subs_open = len(subs_behavior[subs_behavior["opens"] > 0])
current_subs_open = len(
    subs_behavior[(subs_behavior["opens"] > 0) & (subs_behavior["active"])]
)
current_subs_zero = len(
    subs_behavior[(subs_behavior["opens"] == 0) & (subs_behavior["active"])]
)
current_subs_zero_deliver = len(
    subs_behavior[(subs_behavior["delivers"] == 0) & (subs_behavior["active"])]
)

cols = st.columns(5)
cols[0].metric("Unique emails ever sent to", total_subs_ever)
cols[1].metric("Unique emails who read something", total_subs_open)
cols[2].metric("Current subs who read something", current_subs_open)
cols[3].metric("Current subs with zero delivers", current_subs_zero_deliver)
cols[4].metric("Current subs with zero opens", current_subs_zero)

chart_1 = (
    alt.Chart(open_rates)
    .mark_line()
    .encode(x=alt.X("when:O", axis=None), y="rate:Q")
    .properties(height=150)
)
chart_2 = chart_1.mark_bar().encode(
    y="delivers",
    color=alt.Color("type", legend=None),
    tooltip=["title", "delivers", "opens", "rate", "type"],
)

st.altair_chart(chart_1, use_container_width=True)
st.altair_chart(chart_2, use_container_width=True)


with st.expander("Raw open rates"):
    st.write("#### Article open rates")
    st.dataframe(open_rates)

    st.write("#### Susbcriber open rates")
    st.dataframe(subs_behavior)


## SCHEDULE

st.subheader("🗓️ Schedule", divider="red")

left, right = st.columns(2)

with left:
    st.write("#### When are you posting the most?")

    weekday_hour = []
    weekdays = "Mon Tue Wed Thu Fri Sat Sun".split()
    for item in posts_df["email_sent_at"]:
        if isinstance(item, str):
            date = dateparser.parse(item)
            weekday_hour.append(dict(day=weekdays[date.weekday()], hour=date.hour))

    st.altair_chart(
        alt.Chart(pd.DataFrame(weekday_hour))
        .mark_rect()
        .encode(
            x=alt.X("hour:N", title="Hour when email is sent (UTC)"),
            y=alt.Y("day:O", title="Day of the week when email is sent", sort=weekdays),
            color=alt.Color("count()", title="Total"),
        )
        .properties(height=300),
        use_container_width=True,
    )

with right:
    st.write("#### When are your subscribers reading?")

    opens_sample_size = st.sidebar.number_input(
        "Open sample size", min_value=1000, value=min(len(opens), 50000), step=1000
    )

    @st.cache_data
    def compute_open_hours(filename, size):
        weekday_hour = []
        progress = st.sidebar.progress(0, "Processing...")
        weekdays = "Mon Tue Wed Thu Fri Sat Sun".split()

        samples = list(opens["timestamp"])

        if len(samples) > size:
            samples = random.sample(samples, size)

        for i, item in enumerate(samples):
            if i % 1000 == 0:
                progress.progress(
                    (i + 1) / len(samples), f"Processing {i+1}/{len(samples)}"
                )

            if isinstance(item, str):  # 2023-01-15T11:29:51.225Z
                date = datetime.datetime.strptime(item[:-5], r"%Y-%m-%dT%H:%M:%S")
                weekday_hour.append(dict(day=weekdays[date.weekday()], hour=date.hour))

        progress.empty()

        return pd.DataFrame(weekday_hour)

    weekday_hour = compute_open_hours(data.filename, opens_sample_size)

    st.altair_chart(
        alt.Chart(weekday_hour)
        .mark_rect()
        .encode(
            x=alt.X("hour:O", title="Hour when email is opened (UTC)"),
            y=alt.Y(
                "day:O", title="Day of the week when email is opened", sort=weekdays
            ),
            color=alt.Color("count()", title="Total"),
        )
        .properties(height=300),
        use_container_width=True,
    )

word_count = []

for file, text in texts.items():
    words = len(text.split())
    post_id = int(file.orig_filename.split("/")[1].split(".")[0])

    if words > 0:
        word_count.append(
            dict(filename=file.orig_filename, post_id=post_id, words=words)
        )

posts_length = (
    pd.DataFrame(word_count)
    .set_index("post_id")
    .join(open_rates.set_index("post_id"), how="right")
    .reset_index()
)


def compute_time(when):
    date = datetime.datetime.strptime(when[:-5], r"%Y-%m-%dT%H:%M:%S")
    dayofweek = date.weekday()
    hourfraction = (date.hour * 60 + date.minute) / 1440
    return dayofweek + hourfraction


posts_length["time"] = posts_length["when"].apply(compute_time)


st.altair_chart(
    alt.Chart(posts_length)
    .mark_circle()
    .encode(
        x="time",
        y="rate",
        color="type",
        size="words",
        tooltip=["title", "when", "delivers", "opens", "rate"],
    ),
    use_container_width=True,
)

## CONTENT

st.subheader("📰 Content", divider="violet")

left, right = st.columns(2)

with left:
    st.write("#### How long are your posts?")

    st.altair_chart(
        alt.Chart(posts_length)
        .mark_bar()
        .encode(
            x=alt.X("words", bin=True, title="Post length (in words)"),
            y=alt.Y("count()", title="Number of posts"),
        )
        .properties(height=300),
        use_container_width=True,
    )

## MONETIZATION

st.subheader("💲Monetization", divider="green")

st.sidebar.markdown("### Monetization")
st.sidebar.info(
    "The following info cannot be taken from Substack, so please provide it yourself."
)

gar = st.sidebar.number_input(
    "Gross anualized revuene (GAR)", min_value=0.0, format="%.2f", step=10.0
)
target = st.sidebar.number_input(
    "Target GAR", min_value=gar, value=gar, format="%.2f", step=10.0
)

if gar <= 0:
    st.warning(
        "This section requires you to define the Gross Anualized Revenue values in the sidebar.",
        icon="⚠️",
    )
else:
    metric_gar.metric("💲 Current GAR", gar)

    subdollar = len(subs_df) / gar
    targetsub = round(target * subdollar)
    needsubs = targetsub - len(subs_df)
    needdays = needsubs / subs90
    timedelta = datetime.timedelta(days=needdays)
    date = datetime.datetime.today() + timedelta

    target_gar.metric("📆 Days to target GAR", timedelta.days)

    st.write(
        f"""
    - Your current subscriber to dollar ratio is **{subdollar:.2f}** subs/$.
    - To reach your target GAR of **${target}** you'll need around **{targetsub}** free subscribers.
    - Your 90-day average growth rate is **{subs90:.1f} subscribers/day**.
    - At this rate, you'll hit your target GAR on **{timedelta.days} days**, or {date.date()}.
    """
    )
