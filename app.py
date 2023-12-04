import streamlit as st
import dateparser
import datetime
import pandas as pd
import altair as alt
from zipfile import ZipFile
from bs4 import BeautifulSoup


st.set_page_config("Stacklyzer", "📚", "wide")

st.header("Stacklyzer - Simple stats for your Substack!")

st.markdown(
    """This app will help you understand your Substack publication a bit better.
To begin, go to your Settings, navigate to the Exports section, and create a new data export.
Once that is ready, download it, and upload it in the sidebar file input.
We'll take care of the rest."""
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
    progress = st.progress(0, "Parsing posts...")

    texts = {}

    for i, file in enumerate(html_files):
        progress.progress(
            (i + 1) / len(html_files), f"Parsing posts ({i+1}/{len(html_files)})"
        )

        with data.open(file) as fp:
            soup = BeautifulSoup(fp.read(), "html")
            texts[file] = soup.get_text()

    return texts


texts = parse_texts(data.filename)

st.subheader("⭐ Quick info", divider="orange")

cols = st.columns(5)
metric_sub = cols[0].metric("🧑‍🤝‍🧑 Total subscribers", 0)
metric_paid = cols[1].metric("💰 Paid subscribers", 0)
metric_emails = cols[2].metric("📧 Emails sent", 0)
metric_gar = cols[3].metric("💲 Current GAR", 0)
target_gar = cols[4].metric("📆 Days to target GAR", 0)

st.subheader("🧑‍🤝‍🧑 Subscribers", divider="red")

email_list = [f for f in files if f.orig_filename.startswith("email_list")][0]

with data.open(email_list) as fp:
    subs_df = pd.read_csv(fp)

total = len(subs_df)
yearly = len(subs_df[subs_df["plan"] == "yearly"])
comp = len(subs_df[subs_df["plan"] == "comp"])
start_date: datetime.datetime = dateparser.parse(subs_df["created_at"].min())
end_date: datetime.datetime = dateparser.parse(subs_df["created_at"].max())
three_month = end_date - datetime.timedelta(days=90)
weeks = (end_date - start_date).days / 7
avg = len(subs_df) / weeks

subs90 = len(subs_df[subs_df["created_at"] >= str(three_month)]) / 90

metric_sub.metric("🧑‍🤝‍🧑 Total subscribers", len(subs_df), delta=round(avg, 1))
metric_paid.metric("💰 Paid subscribers", yearly)

st.info(
    f"You have **{len(subs_df)}** active subscribers, including **{yearly} paid** and **{comp} active comps**, averaging **{avg:.1f}** new subscribers per week.",
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


st.subheader("📧 Posts", divider="blue")

with data.open("posts.csv") as fp:
    posts_df = pd.read_csv(fp)

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
    st.dataframe(posts_df)

left, right = st.columns([2, 1])

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
            color=alt.Color("count()", title="Total emails sent"),
        )
        .properties(height=300),
        use_container_width=True,
    )


word_count = []

for file, text in texts.items():
    words = len(text.split())
    if words > 0:
        word_count.append(dict(filename=file.orig_filename, words=words))

with right:
    st.write("### How long are your posts?")

    df = pd.DataFrame(word_count)
    st.altair_chart(
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("words", bin=True, title="Post length (in words)"),
            y=alt.Y("count()", title="Number of posts"),
        )
        .properties(height=300),
        use_container_width=True,
    )


st.subheader("💲Monetization", divider="green")

st.sidebar.markdown("### Monetization")
st.sidebar.info(
    "The following info cannot be taken from Substack, so please provide it yourself."
)

gar = st.sidebar.number_input(
    "Gross anualized revuene (GAR)", min_value=1.0, format="%.2f", step=10.0
)
target = st.sidebar.number_input(
    "Target GAR", min_value=gar, value=gar, format="%.2f", step=10.0
)

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
