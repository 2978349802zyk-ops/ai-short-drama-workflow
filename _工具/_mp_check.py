
import moviepy
print("moviepy", moviepy.__version__)
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
print("core imports OK")
try:
    from moviepy import vfx, afx
    print("vfx/afx OK; CrossFadeIn:", hasattr(vfx,"CrossFadeIn"), "MultiplySpeed:", hasattr(vfx,"MultiplySpeed"))
    print("afx:", [x for x in ["VolumeX","AudioFadeIn","AudioFadeOut","MultiplexAudio","CompositeAudioClip"] if hasattr(afx,x)])
except Exception as e:
    print("vfx/afx err", e)
import inspect
try:
    from moviepy import TextClip
    print("TextClip sig:", str(inspect.signature(TextClip.__init__))[:300])
except Exception as e:
    print("TextClip err", e)
