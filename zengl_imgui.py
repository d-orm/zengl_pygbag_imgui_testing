import struct
import imgui
import zengl
import _zengl
import pygame
import platform
import sys

stolen_symbols = None

def web_context_pyodide():
    class m_canvas:
        def getCanvas3D(self, name='canvas',width=0,height=0):
            canvas = platform.document.getElementById(name)
            try:
                width = width or canvas.width
                height = height or canvas.height
                #print(f"canvas size was previously set to : {width=} x {height=}")
            except:
                pass
            canvas.width = width or 1024
            canvas.height = height or 1024
            return canvas

    class m_pyodide_js:
        canvas = m_canvas()
        _module = platform.window

    sys.modules["pyodide_js"] = m_pyodide_js()
    del m_canvas
    del m_pyodide_js
    import js
    import pyodide_js

    canvas = pyodide_js.canvas.getCanvas3D()
    if canvas is None:
        canvas = js.document.getElementById('canvas')
    if canvas is None:
        canvas = js.document.createElement('canvas')
        canvas.id = 'canvas'
        canvas.style.position = 'fixed'
        canvas.style.top = '0'
        canvas.style.right = '0'
        canvas.style.zIndex = '10'
        js.document.body.appendChild(canvas)
        pyodide_js.canvas.setCanvas3D(canvas)
    gl = canvas.getContext(
        'webgl2',
        'high-performance',
        False,
        False,
        False,
        False,
        False,
    )
    callback = js.window.eval(zengl._extern_gl)
    symbols = callback(pyodide_js._module, gl)
    pyodide_js._module.mergeLibSymbols(symbols)
    global stolen_symbols
    stolen_symbols = symbols


zengl._extern_gl = zengl._extern_gl.replace('return {', 'return { zengl_glScissor(x, y, w, h) { gl.scissor(x, y, w, h); },')
_zengl.web_context_pyodide = web_context_pyodide


class OpenGL:
    GL_TEXTURE0 = 0x84c0
    GL_TEXTURE_2D = 0xde1
    GL_ARRAY_BUFFER = 0x8892
    GL_ELEMENT_ARRAY_BUFFER = 0x8893
    GL_STREAM_DRAW = 0x88e0
    GL_TRIANGLES = 0x0004
    GL_UNSIGNED_INT = 0x1405
    GL_SCISSOR_TEST = 0x0c11

    def __init__(self, load):
        self.glEnable = stolen_symbols.zengl_glEnable
        self.glDisable = stolen_symbols.zengl_glDisable
        self.glScissor = stolen_symbols.zengl_glScissor
        self.glActiveTexture = stolen_symbols.zengl_glActiveTexture
        self.glBindTexture = stolen_symbols.zengl_glBindTexture
        self.glBindBuffer = stolen_symbols.zengl_glBindBuffer
        self.glBufferData = stolen_symbols.zengl_glBufferData
        self.glDrawElements = stolen_symbols.zengl_glDrawElements


class ZenGLRenderer:
    def __init__(self):
        self.io = imgui.get_io()
        self.ctx = zengl.context()

        self.vertex_buffer = self.ctx.buffer(size=1)
        self.index_buffer = self.ctx.buffer(size=1, index=True)

        width, height, pixels = self.io.fonts.get_tex_data_as_rgba32()
        self.atlas = self.ctx.image((width, height), 'rgba8unorm', pixels)

        self.pipeline = self.ctx.pipeline(
            vertex_shader='''
                #version 300 es
                precision highp float;
                uniform vec2 Scale;
                layout (location = 0) in vec2 in_vertex;
                layout (location = 1) in vec2 in_uv;
                layout (location = 2) in vec4 in_color;
                out vec2 v_uv;
                out vec4 v_color;
                void main() {
                    v_uv = in_uv;
                    v_color = in_color;
                    gl_Position = vec4(in_vertex.xy * Scale - 1.0, 0.0, 1.0);
                    gl_Position.y = -gl_Position.y;
                }
            ''',
            fragment_shader='''
                #version 300 es
                precision highp float;
                uniform sampler2D Texture;
                in vec2 v_uv;
                in vec4 v_color;
                layout (location = 0) out vec4 out_color;
                void main() {
                    out_color = texture(Texture, v_uv) * v_color;
                }
            ''',
            layout=[
                {'name': 'Texture', 'binding': 0},
            ],
            resources=[
                {
                    'type': 'sampler',
                    'binding': 0,
                    'image': self.atlas,
                    'min_filter': 'nearest',
                    'mag_filter': 'nearest',
                },
            ],
            blend={
                'enable': True,
                'src_color': 'src_alpha',
                'dst_color': 'one_minus_src_alpha',
            },
            uniforms={
                'Scale': [0.0, 0.0],
            },
            topology='triangles',
            framebuffer=None,
            viewport=(0, 0, 0, 0),
            vertex_buffers=zengl.bind(self.vertex_buffer, '2f 2f 4nu1', 0, 1, 2),
            index_buffer=self.index_buffer,
            instance_count=0,
        )

        self.gl = OpenGL(zengl.default_loader.load_opengl_function)
        self.vtx_buffer = zengl.inspect(self.vertex_buffer)['buffer']
        self.idx_buffer = zengl.inspect(self.index_buffer)['buffer']
        self.io.fonts.texture_id = zengl.inspect(self.atlas)['texture']
        self.io.fonts.clear_tex_data()

    def render(self, draw_data=None):
        if draw_data is None:
            draw_data = imgui.get_draw_data()

        display_width, display_height = self.io.display_size
        fb_width = int(display_width * self.io.display_fb_scale[0])
        fb_height = int(display_height * self.io.display_fb_scale[1])

        if draw_data is None or fb_width == 0 or fb_height == 0:
            return

        self.pipeline.viewport = (0, 0, fb_width, fb_height)
        self.pipeline.uniforms['Scale'][:] = struct.pack('2f', 2.0 / display_width, 2.0 / display_height)
        self.pipeline.render()

        gl = self.gl
        gl.glEnable(gl.GL_SCISSOR_TEST)
        gl.glActiveTexture(gl.GL_TEXTURE0)
        for commands in draw_data.commands_lists:
            idx_buffer_offset = 0
            vtx_size = commands.vtx_buffer_size * imgui.VERTEX_SIZE
            idx_size = commands.idx_buffer_size * imgui.INDEX_SIZE
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vtx_buffer)
            gl.glBufferData(gl.GL_ARRAY_BUFFER, vtx_size, commands.vtx_buffer_data, gl.GL_STREAM_DRAW)
            gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.idx_buffer)
            gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, idx_size, commands.idx_buffer_data, gl.GL_STREAM_DRAW)
            for command in commands.commands:
                x1, y1, x2, y2 = command.clip_rect
                gl.glScissor(int(x1), int(fb_height - y2), int(x2 - x1), int(y2 - y1))
                gl.glBindTexture(gl.GL_TEXTURE_2D, command.texture_id)
                gl.glDrawElements(gl.GL_TRIANGLES, command.elem_count, gl.GL_UNSIGNED_INT, idx_buffer_offset)
                idx_buffer_offset += command.elem_count * imgui.INDEX_SIZE
        gl.glDisable(gl.GL_SCISSOR_TEST)


class PygameBackend:
    def __init__(self):
        # from imgui.integrations.pygame import PygameRenderer
        # class PygameInputHandler(PygameRenderer):
        #     def __init__(self):
        #         self._gui_time = None
        #         self.custom_key_map = {}
        #         try:
        #             imgui.get_io()
        #         except:
        #             imgui.create_context()
        #         self.io = imgui.get_io()
        #         self.io.display_size = pygame.display.get_window_size()
        #         self._map_keys()
        # self.input_handler = PygameInputHandler()
        imgui.create_context()
        self.io = imgui.get_io()
        self.io.display_size = pygame.display.get_window_size()
        self.renderer = ZenGLRenderer()

    def render(self):
        return self.renderer.render()

    def process_event(self, event):
        pass
        # return self.input_handler.process_event(event)

    def process_inputs(self):
        pass
        # return self.input_handler.process_inputs()