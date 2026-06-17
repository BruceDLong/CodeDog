Timers and Animation Frames
===========================

CodeDog has two related timer concepts with different contracts.

``callPeriodically``
--------------------

``callPeriodically`` is the legacy repeating timer API. Its original Java
library declaration is:

.. code-block:: dog

   me timeOutID: callPeriodically(me string: varClass, me string: funcToCall, me int: microSecs): COMMAND_addImplements="Runnable:ToClass:%1" <- <%!%GScheduledExecutorService timerID=Executors.newSingleThreadScheduledExecutor(); timerID.scheduleAtFixedRate(%2, 0, %3, TimeUnit.MILLISECONDS)%>

Typical call sites pass the class token, the object to schedule, and an
interval:

.. code-block:: dog

   callPeriodically(RandomGen, randomGenSrc, 50)

The first argument is used by ``COMMAND_addImplements`` so the generated Java
class implements ``Runnable``. The second argument is emitted as the runnable
object passed to the platform timer. The scheduled object must provide:

.. code-block:: dog

   void: run() <- {
       ...
   }

``callPeriodically`` repeats until the platform timer is explicitly stopped by
platform code. The ``run()`` return value has no timer semantics.

``callOnce``
------------

``callOnce`` is a one-shot scheduling primitive used when the scheduled method
should run once after a delay. It takes a class token, an object, a method name,
and an interval:

.. code-block:: dog

   callOnce("DashboardWidget", self, "animationFrameTimerFired", frameMillis)

The method name is emitted directly by the translator. The scheduled method
does not need to be named ``run`` and does not return a continuation value.

Dashboard animation frames
--------------------------

``DashboardWidget.requestAnimationFrame()`` and
``DashboardWidget.requestAnimationFrameRectIn()`` use ``callOnce``. When the
one-shot timer fires, Dashboard calls ``animationFrameTimerFired()``. That
method calls ``tweenTick(event)``, redraws the affected area, and schedules
another one-shot frame only when ``tweenTick`` returns ``true``.

This keeps animation-frame continuation state inside Dashboard and avoids
reserving the generic method name ``run`` on every ``DashboardWidget`` subclass.
