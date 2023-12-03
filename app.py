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
Once that is ready, download it, and upload it in the following file input.
We'll take care of the rest."""
)

data_fp = st.file_uploader("Upload your Substack data dump here.", type="zip")
st.header("", divider="rainbow")

if not data_fp:
    st.warning("Upload your data to continue.", icon="🔥")
    st.stop()

data = ZipFile(data_fp)
files = data.filelist


st.subheader("🧑‍🤝‍🧑 Subscribers", divider="blue")

email_list = [f for f in files if f.orig_filename.startswith("email_list")][0]

with data.open(email_list) as fp:
    subs_df = pd.read_csv(fp)

total = len(subs_df)
yearly = len(subs_df[subs_df["plan"] == "yearly"])
comp = len(subs_df[subs_df["plan"] == "comp"])
start_date: datetime.datetime = dateparser.parse(subs_df['created_at'].min())
end_date:datetime.datetime = dateparser.parse(subs_df['created_at'].max())
weeks = (end_date - start_date).days / 7
avg = len(subs_df) / weeks

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

published = posts_df[posts_df['email_sent_at'].notnull()]
start_date: datetime.datetime = dateparser.parse(published['email_sent_at'].min())
end_date:datetime.datetime = dateparser.parse(published['email_sent_at'].max())
weeks = (end_date - start_date).days / 7
avg = len(published) / weeks
newsletters = len(published[published["type"] == "newsletter"])

st.info(f"💌 So far you've sent **{len(published)}** emails, averaging **{avg:.1f} posts per week**. Of these, **{newsletters}** are original newsletter posts.")

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

st.write("#### At what time of day are you posting the most?")

weekday_hour = []
weekdays = "Sun Mon Tue Wed "
for item in posts_df['email_sent_at']:
    if isinstance(item, str):
        date = dateparser.parse(item)
        weekday_hour.append(dict(day=date.weekday(), hour=date.hour))


st.altair_chart(alt.Chart(pd.DataFrame(weekday_hour)).mark_rect().encode(
    x=alt.X("hour:N", title="Hour when email is sent (UTC)"),
    y=alt.Y("day:O", title="Day of the week when email is sent"),
    color=alt.Color("count()", title='Total emails sent'),
), use_container_width=True)


progress = st.progress(0, "Parsing posts...")
html_files = [f for f in data.filelist if f.orig_filename.endswith(".html")]

word_count = []

for i, file in enumerate(html_files):
    progress.progress((i+1) / len(html_files), f"Parsing posts ({i+1}/{len(html_files)})")

    with data.open(file) as fp:
        soup = BeautifulSoup(fp.read(), "html")
        words = len(soup.get_text(" ", strip=True).split())

        if words > 0:
            word_count.append(dict(filename=file.orig_filename, words=words))

df = pd.DataFrame(word_count)
st.write(df)
