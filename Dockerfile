# Container image that runs your code
FROM alpine

RUN apk --update --no-cache add git python py-pip npm perl
RUN pip install coverage wheel colorama unidiff
RUN npm install -g diff-so-fancy
RUN hash -r
RUN git config --system user.email "58579435+EasyCov-bot@users.noreply.github.com"
RUN git config --system user.name "EasyCov Bot"
RUN git config --system core.pager "diff-so-fancy | less --tabs=4 -RFX"
RUN git config --system diff-so-fancy.rulerWidth 50
RUN git config --system diff-so-fancy.first-run false
RUN git config --system color.ui true
RUN git config --system color.diff-highlight.oldNormal    "red bold noul"
RUN git config --system color.diff-highlight.oldHighlight "red bold ul"
RUN git config --system color.diff-highlight.newNormal    "green bold noul"
RUN git config --system color.diff-highlight.newHighlight "green bold ul"
RUN git config --system color.diff.meta       "yellow"
RUN git config --system color.diff.frag       "magenta bold"
RUN git config --system color.diff.commit     "yellow bold"
RUN git config --system color.diff.old        "red bold"
RUN git config --system color.diff.new        "green bold"
RUN git config --system color.diff.whitespace "black red"

COPY . /root/EasyCov/
RUN pip install /root/EasyCov
RUN hash -r

# Code file to execute when the docker container starts up (`entrypoint.sh`)
# TODO: This speeds up debugging.  Change the entrypoint back to /root/EasyCov/action.py
ENTRYPOINT ["python", "/github/workspace/action.py"]
