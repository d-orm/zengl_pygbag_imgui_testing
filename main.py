# /// script
# dependencies = [
#     "zengl",
#     "pygame-ce",
# ]
# ///

import zengl_imgui_pygbag_override

import asyncio
from zengl_imgui import PygameBackend
import imgui_demo_frame
import pygame
import zengl

screen_size = (800, 600)
pygame.display.set_mode(screen_size, pygame.OPENGL)
ctx = zengl.context()
impl = PygameBackend()
image = ctx.image(screen_size, 'rgba8unorm')
image.clear_value = (0.5, 0.0, 0.0, 1.0)


async def main():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            impl.process_event(event)
        impl.process_inputs()
        
        ctx.new_frame()
        image.clear()
        image.blit()

        imgui_demo_frame.run()
        impl.render()

        ctx.end_frame()
        pygame.display.flip()
        await asyncio.sleep(0)

asyncio.run(main())