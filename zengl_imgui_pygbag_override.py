import zengl
import _zengl
import zengl_imgui
stolen_symbols = None
def web_context_pyodide():
    import js
    import zengl
    import json

    options = js.window.JSON.parse(json.dumps(dict(
        powerPreference="high-performance",
        premultipliedAlpha=False,
        antialias=False,
        alpha=False,
        depth=False,
        stencil=False,
    )))

    canvas = js.document.getElementById('canvas')
    gl = canvas.getContext(
        'webgl2',
        options,
    )
    callback = js.window.eval(zengl._extern_gl)
    symbols = callback(js.window, gl)
    js.window.mergeLibSymbols(symbols)
    global stolen_symbols
    stolen_symbols = symbols

class OpenGL:
    GL_TEXTURE0 = 0x84c0
    GL_TEXTURE_2D = 0xde1
    GL_ARRAY_BUFFER = 0x8892
    GL_ELEMENT_ARRAY_BUFFER = 0x8893
    GL_STREAM_DRAW = 0x88e0
    GL_TRIANGLES = 0x0004
    GL_UNSIGNED_INT = 0x1405
    GL_SCISSOR_TEST = 0x0c11

    def __init__(self):
        self.glEnable = stolen_symbols.zengl_glEnable
        self.glDisable = stolen_symbols.zengl_glDisable
        self.glScissor = stolen_symbols.zengl_glScissor
        self.glActiveTexture = stolen_symbols.zengl_glActiveTexture
        self.glBindTexture = stolen_symbols.zengl_glBindTexture
        self.glBindBuffer = stolen_symbols.zengl_glBindBuffer
        self.glBufferData = stolen_symbols.zengl_glBufferData
        self.glDrawElementsInstanced = stolen_symbols.zengl_glDrawElementsInstanced

if zengl._extern_gl:
    zengl_imgui.OpenGL = OpenGL
    zengl._extern_gl = zengl._extern_gl.replace('return {', 'return { zengl_glScissor(x, y, w, h) { gl.scissor(x, y, w, h); },')
    zengl._extern_gl = zengl._extern_gl.replace('gl.bufferData(target, size, usage);', 'gl.bufferData(target, size, usage); gl.bufferSubData(target, 0, wasm.HEAPU8.subarray(data, data + size));')
    _zengl.web_context_pyodide = web_context_pyodide
    ctx = zengl.context()
