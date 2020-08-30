import os
import datetime

PROFILE_LOG_BASE = '/home/ubuntu/Desktop/profiling/profiles/'


def profile_func(filename):
    """Function/method decorator that will cause only the decorated callable
        to be profiled and saved to the specified file.

        @type  filename: str
        @param filename: The filename to write the profile to."""
    if not os.path.isabs(filename):
        filename = os.path.join(PROFILE_LOG_BASE, filename)

    def proffunc(f):
        def profiled_func(*args, **kwargs):
            import cProfile
            import logging

            (base, ext) = os.path.splitext(filename)
            base = base + "-" + datetime.datetime.now().strftime("%Y%m%dT%HH%MM%SS%f")
            final_log_file = base + ext

            logging.info('Profiling function %s' % (f.__name__))

            try:
                profiler = cProfile.Profile()
                retval = profiler.runcall(f, *args, **kwargs)
                profiler.getstats()
                profiler.dump_stats(final_log_file)
            except IOError:
                logging.exception("Could not open profile file '%(filename)s'" % {
                                  "filename": final_log_file})

            return retval

        return profiled_func
    return proffunc
