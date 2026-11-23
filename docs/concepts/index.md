# How fmx works

A **bench** is one Frappe site with everything it needs, running as its own set of containers: the web process, an nginx in front of it, background workers, a scheduler, socketio, and a cache and a queue Redis.

Two independent axes describe every bench.

| Axis | Question it answers | Values |
|---|---|---|
| [Runtime](runtimes.md) | Where does the code live? | `mount`: an editable workspace on your disk. `image`: an immutable, pre-built Docker image |
| [Environment](environments.md) | How does the web process run? | `dev`: auto-reloading dev server. `prod`: Gunicorn, restart on crash |

They combine freely, and all four combinations are useful:

| Runtime | `dev` | `prod` |
|---|---|---|
| **`mount`** | The daily development loop: edit code, see it live | Simple production: editable code, production web server |
| **`image`** | Testing a release image locally | Immutable production: deploys, rollbacks, rolling swaps |

Most other questions about a bench, can you edit code in place, does a change need a rebuild, how does a restart behave, come down to these two axes.

<div class="grid cards" markdown>

-   :lucide-box:{ .lg .middle } &nbsp; **[Runtimes: mount vs image](runtimes.md)**

    ---

    The fundamental choice: editable workspace or immutable image. What each can do, and how to move between them.

-   :lucide-toggle-left:{ .lg .middle } &nbsp; **[Environments: dev vs prod](environments.md)**

    ---

    The web-process mode: auto-reloading dev server vs Gunicorn, and the defaults that come with each.

</div>

## What is shared and what is not

One machine runs many benches. They share exactly two things:

- **One MariaDB server** holding every bench's database.
- **One nginx proxy** on ports 80 and 443, routing each request to the right bench by domain.

`fmx services` manages those two. Everything else belongs to a single bench.

A bench can skip the shared database at create time by pointing at an external server; after that, only the CA is editable, with `fmx update --db-ca`. Redis is more flexible: either side, cache or queue, can move to an external server at create time or later, and back again. `fmx update --redis-cache` and `--redis-queue` point a side out; `--no-redis-cache`, `--no-redis-queue`, or `--no-redis` bring it back to fmx's own container.

## How a bench actually runs

<div class="grid cards" markdown>

-   :lucide-globe:{ .lg .middle } &nbsp; **[Web serving and concurrency](web-serving.md)**

    ---

    The request path and the web process: dev server vs Gunicorn, workers and threads, when to tune.

-   :lucide-list-checks:{ .lg .middle } &nbsp; **[Background jobs and workers](background-jobs.md)**

    ---

    RQ queues, the worker containers, the scheduler, safe restarts and draining.

-   :lucide-network:{ .lg .middle } &nbsp; **[Architecture](../reference/architecture.md)**

    ---

    What is actually running: containers per bench, shared global services, networks, and volumes.

</div>
