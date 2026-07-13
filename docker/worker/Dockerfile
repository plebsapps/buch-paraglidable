# Stage D3: worker image = the frozen pipeline image (Python 3.6/TF, built
# from ./docker as "paraglidable") plus APScheduler. The base is pinned by
# being a locally built, frozen artifact — see docs/plan.md (stage A/B).
FROM paraglidable

# Last APScheduler line supporting Python 3.6; tzlocal pinned to the
# matching major version (3.x dropped py3.6). The frozen image runs as
# user "paraglidable" -> switch to root only for the install.
# psycopg2-binary 2.8.6: letzte Linie mit cp36-Wheels (Etappe E, DB-Spiegel).
USER root
RUN pip3 install --no-cache-dir apscheduler==3.9.1 tzlocal==2.1 psycopg2-binary==2.8.6
USER paraglidable

WORKDIR /workspaces/Paraglidable
CMD ["python3", "-u", "pipeline/scheduler.py"]
