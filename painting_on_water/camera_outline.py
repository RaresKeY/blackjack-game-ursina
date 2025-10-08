from ursina import window, color, camera
from panda3d.core import (
    FrameBufferProperties, GraphicsPipe, Texture, GraphicsOutput,
    Shader, Vec2, BitMask32
)
# Note: CardMaker is no longer needed here
from direct.filter.FilterManager import FilterManager

CAM_OUTLINE_SHADERS = "Assets/Shaders/cam_outline/"

def outline_camera_prep():
    W, H = map(int, window.size)

    # --- Main scene capture (ONE call) ---
    manager = FilterManager(base.win, base.cam)
    scene_tex = Texture()
    quad = manager.renderSceneInto(colortex=scene_tex)
    manager.buffers[-1].setSize(W, H)  # match window exactly

    # --- Mask buffer ---
    fbprops = FrameBufferProperties()
    fbprops.setRgbColor(True)
    fbprops.setAlphaBits(8)
    fbprops.setDepthBits(1)
    fbprops.setMultisamples(8)  # crisper mask edges

    winprops = base.win.getProperties()
    mask_buf = base.graphicsEngine.makeOutput(
        base.pipe, "mask", -2,
        fbprops, winprops,
        GraphicsPipe.BFRefuseWindow,
        base.win.getGsg(), base.win
    )
    mask_buf.setClearColorActive(True)
    mask_buf.setClearColor((0, 0, 0, 0))
    mask_buf.setSize(W, H)
    fbprops.setMultisamples(8)

    mask_tex = Texture()
    mask_buf.addRenderTexture(
        mask_tex,
        GraphicsOutput.RTMCopyTexture,
        GraphicsOutput.RTPColor
    )

    # --- Mask camera: MATCH lens + transform ---
    mask_cam = base.makeCamera(mask_buf)
    mask_cam.node().setLens(base.cam.node().getLens())   # share exact lens
    mask_cam.reparentTo(base.cam)                        # follow cam transform
    mask_cam.node().setCameraMask(BitMask32.bit(1))

    # --- Post shader ---
    cam_outline = Shader.load(
        Shader.SLGLSL,
        CAM_OUTLINE_SHADERS + "cam_outline.vert",
        CAM_OUTLINE_SHADERS + "cam_outline.frag"
    )

    # Clamp to window to prevent outline wrap
    scene_tex.setWrapU(Texture.WMClamp)
    scene_tex.setWrapV(Texture.WMClamp)
    mask_tex.setWrapU(Texture.WMClamp)
    mask_tex.setWrapV(Texture.WMClamp)


    quad.setShader(cam_outline)
    quad.setShaderInput("scene_tex", scene_tex)
    quad.setShaderInput("mask_tex", mask_tex)
    quad.setShaderInput("screen_size", Vec2(mask_tex.getXSize(), mask_tex.getYSize()))
    quad.setShaderInput("thickness", 2.0)  # pixels, keep small
    quad.setShaderInput("outline_color", color.rgba(1, 1, 0, 1))
    quad.setShaderInput("inner_px", 2.0)   # leave 1px around object
    quad.setShaderInput("outer_px", 8.0)   # halo starts farther out
        
    return mask_cam
