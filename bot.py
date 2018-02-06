#!/usr/bin/env python3.6

import sys
import time
import textwrap
import datetime as dt
from croniter import croniter
import slack
import gerrit
import database


class PostableChange:
    def __init__(self, gerrit_change):
        self._gerrit_change = gerrit_change

    @property
    def cr(self):
        return self._gerrit_change.code_review

    @property
    def ver(self):
        return self._gerrit_change.verified

    @property
    def url(self):
        return self._gerrit_change.url

    @property
    def username(self):
        return self._gerrit_change.username

    @property
    def subject(self):
        return slack.escape(self._gerrit_change.subject)

    @property
    def code_review_icon(self):
        if self.cr == gerrit.CodeReview.PLUS_ONE:
            return slack.Emoji.PLUS_ONE
        elif self.cr == gerrit.CodeReview.PLUS_TWO:
            return slack.Emoji.PLUS_ONE * 2
        elif self.cr == gerrit.CodeReview.MISSING:
            return slack.Emoji.EXCLAMATION
        elif self.cr == gerrit.CodeReview.MINUS_ONE:
            return slack.Emoji.POOP
        elif self.cr == gerrit.CodeReview.MINUS_TWO:
            return slack.Emoji.JS

    @property
    def verified_icon(self):
        if self.ver == gerrit.Verified.MISSING:
            return ''
        elif self.ver == gerrit.Verified.VERIFIED:
            return slack.Emoji.WHITE_CHECK_MARK
        elif self.ver == gerrit.Verified.FAILED:
            return slack.Emoji.X

    @property
    def color(self):
        if self.cr == gerrit.CodeReview.PLUS_TWO:
            return '#36a64f'
        elif self.cr == gerrit.CodeReview.PLUS_ONE and self.ver == gerrit.Verified.VERIFIED:
            return '#DBF32D'
        else:
            return '#EC1313'

    def full_message(self):
        text = f'CR: {self.code_review_icon} V: {self.verified_icon} - {self.username}: {self.subject}'
        # Slack wraps lines around 80? width, so if we cut out here explicitly,
        # every patch will fit in one line
        return textwrap.shorten(text, width=80, placeholder=' …')


class CronTime:
    def __init__(self, crontab):
        self._crontab = crontab
        # This way, we will miss this very minute at startup to avoid sending the same message twice.
        self._cron = croniter(crontab, start_time=dt.datetime.now())
        self.calc_next()

    def __str__(self):
        return self._crontab

    def __repr__(self):
        return f'CronTime({self._crontab})'

    def calc_next(self):
        self.next = self._cron.get_next(dt.datetime)


class CronJob:
    def __init__(self, gerrit_url, gerrit_query, slack_webhook_url, slack_channel):
        self._gerrit = gerrit.Client(gerrit_url, gerrit_query)
        self._slack_channel = slack.Channel(slack_webhook_url, slack_channel)

    def __str__(self):
        return f'{self._gerrit.query} -> {self._slack_channel}'

    def __repr__(self):
        return f"CronJob(query='{self._gerrit.query}', channel='{self._slack_channel}')"

    def run(self):
        changes = [PostableChange(c) for c in self._gerrit.get_changes()]
        if not changes:
            return True

        summary_text = f'{len(changes)} patch vár review-ra:'
        summary_link = slack.make_link(self._gerrit.changes_url, summary_text)
        attachments = [slack.make_attachment(c.color, c.full_message(), c.url) for c in changes]

        res = self._slack_channel.post(summary_link, attachments)
        if not res.ok:
            print(f'{res.status_code} error requesting {res.url} for channel {self._channel}:',
                  res.text, file=sys.stderr)
            return False

        return True


def main():
    db = database.Database()
    gerrit_url = db.load_environment().GERRIT_URL
    crontab = [(CronTime(row['crontab']), CronJob(gerrit_url, row['gerrit_query'], row['webhook_url'], row['channel']))
               for row in db.load_crontabs()]
    db.close()
    print(crontab)

    while True:
        now = dt.datetime.now()
        rounded_now = now.replace(second=0, microsecond=0)
        print(now, 'Checking crontabs to run...')

        for cron_time, job in crontab:
            if cron_time.next == rounded_now:
                print('Running job...', job)
                job.run()
                cron_time.calc_next()

        time.sleep(5)


if __name__ == '__main__':
    main()
