import numpy as np
import pygame as pg
import glm

import time
from function import *

class BaseModel:
    def __init__(self, app, pos=(0,0,0), rot = (0,0,0), scale = (1,1,1), tex_id=0, vao_name='cube', set_scale=False, name = None):
        self.app = app
        self.original_pos = glm.vec3(pos)
        self.position = glm.vec3(pos)
        self.rotation = glm.vec3(rot)
        self.scale = glm.vec3(scale)
        self.set_scale = set_scale
        self.m_model = self.get_model_matrix(app)
        self.tex_id = tex_id
        self.name = vao_name
        if name != None: # if we want a specific name from the start
            self.name = name
        
        self.vao_name = vao_name
        self.vao = self.app.mesh.vao.vaos[vao_name]
        self.shader_program = self.vao.program 
        self.camera = self.app.camera

    def on_init_vao(self, vao_name):
        self.vao_name = vao_name
        self.vao = self.app.mesh.vao.vaos[vao_name]
        self.shader_program = self.vao.program 
        self.set_scale = True
        if vao_name in ["cube", "pyramid"]:
            self.set_scale = False
        self.m_model = self.get_model_matrix(self.app)
        
    def update(self): ...

    def get_model_matrix(self, app):
        m_model = glm.mat4()
        if self.set_scale:
            m_model = glm.translate(m_model, glm.vec3(self.position.x, self.position.y-self.scale.y, self.position.z))
        else:
            m_model = glm.translate(m_model, self.position)

        m_model = glm.rotate(m_model, glm.radians(self.rotation).x, glm.vec3(1,0,0))
        m_model = glm.rotate(m_model, glm.radians(self.rotation).y, glm.vec3(0,1,0))
        m_model = glm.rotate(m_model, glm.radians(self.rotation).z, glm.vec3(0,0,1))
        
        if self.set_scale:
            m_model = glm.scale(m_model, ((self.scale.x,self.scale.z,self.scale.y)/(app.mesh.vao.scales[-1]/2)))
        else:
            m_model = glm.scale(m_model, (self.scale.x,self.scale.z,self.scale.y))
        return m_model

    def buffer_lights(self):
        LIGHT_POS = []
        LIGHT_COL = []
        LIGHT_INT = []
        for light in self.app.lights:
            light_pos = light.position
            light_col = light.color
            light_int = light.intensity
            LIGHT_POS.append(light_pos)
            LIGHT_COL.append(light_col)
            LIGHT_INT.append(light_int)
        while len(LIGHT_POS) < 4: #we have 4 lights max
            light_pos = (0,0,0)
            light_col = (0,0,0)
            light_int = 0
            LIGHT_POS.append(light_pos)
            LIGHT_COL.append(light_col)
            LIGHT_INT.append(light_int)

        LIGHT_POS = np.array(LIGHT_POS, dtype = 'f4')
        LIGHT_COL = np.array(LIGHT_COL, dtype = 'f4')
        LIGHT_INT = np.array(LIGHT_INT, dtype = 'f4')
        
        self.shader_program['light_pos'].write(LIGHT_POS)
        self.shader_program['light_color'].write(LIGHT_COL)
        self.shader_program['light_intensity'].write(LIGHT_INT)

    def render(self):
        self.update()
        self.vao.render()
    
    def destroy(self):
        if self in [light.light_ui for light in self.app.lights]:
            self.light.destroy()
        else:
            self.app.scene.remove(self)

class Cube(BaseModel):
    def __init__(self, app, pos=(0,0,0), rot=(0,0,0), scale=(1,1,1), tex_id=0, vao_name='cube', name = None):
        super().__init__(app, pos, rot, scale, tex_id, vao_name, name=name)
        self.on_init()

    def update(self):
        self.texture.use(location = 0)
        #matrices
        self.shader_program['m_proj'].write(self.camera.m_proj)
        self.shader_program['m_view'].write(self.camera.m_view)
        self.shader_program['cam_pos'].write(self.camera.position)
        self.shader_program['m_model'].write(self.m_model)
        #light
        self.buffer_lights()

    def update_shadow(self, indice, face):
        number_mat = []
        number_lights = 0
        m_views = []
        m_proj_ls= []

        for i in range(len(self.app.scene_renderer.shadowMapList)):
            number_lights+=1
            self.depth_texture = self.app.mesh.texture.textures['depth_texture'][i]
            nb = 0
            for e in number_mat:
                nb+=e
            if type(self.depth_texture) == list:
                number_mat.append(6)                    #self.shader_program['number_mat'] = 6
                                                        #m_view = glm.array(self.app.lights[i].m_view_l)
                #depth texture
                for y in range(6):
                    self.depth_texture[y].use(location=1+y+nb)
                    if (len(self.app.lights)>i):
                        m_views.append(self.app.lights[i].m_view_l[y])
            else:
                number_mat.append(1)
                for _ in range(6):
                    m_views.append(self.app.lights[i].m_view_l)
                                                               #m_view = glm.array([self.app.lights[i].m_view_l for _ in range(6)])
                #depth texture
                self.depth_texture.use(location=1+nb)
                
            #self.shader_program['m_view_l'].write(m_view.to_bytes())

            m_proj_ls.append(self.app.lights[i].m_proj_l)

        m_view_l = glm.array(m_views+[glm.mat4() for _ in range(24-len(m_views))])
        m_proj_l = glm.array(m_proj_ls+[glm.mat4() for _ in range(4-len(m_proj_ls))])
        self.shader_program['number_mat'] = np.array(number_mat+[0 for _ in range(4-len(number_mat))])
        self.shader_program['number_lights'] = number_lights
        self.shader_program['m_view_l'].write(m_view_l.to_bytes())
        self.shader_program['m_proj_l'].write(m_proj_l.to_bytes())
        #shadow program (indice)
        if face != -1:
            self.shadow_program['m_view_l'].write(self.app.lights[indice].m_view_l[face])
        else:
            self.shadow_program['m_view_l'].write(self.app.lights[indice].m_view_l)

        self.shadow_program['m_proj'].write(self.app.lights[indice].m_proj_l)
        self.shadow_program['m_model'].write(self.m_model)

    def render_shadow(self, indice, face):
        self.update_shadow(indice, face)
        self.shadow_vao.render()

    def on_init(self):
        #shadow
        self.shadow_vao = self.app.mesh.vao.vaos['shadow_'+self.vao_name]
        self.shadow_program=self.shadow_vao.program

        self.depth_texture = self.app.mesh.texture.textures['depth_texture'][0]
        self.shader_program['shadowMap'] = [i for i in range(1,25)]
        self.shader_program['number_lights'] = 1
        
        if self.app.lights[0].type_of_light == 'point':
            self.shader_program['number_mat'] = [6 for _ in range(4)]
            mv=[]
            for i in range(24):
                mv.append(self.app.lights[0].m_view_l[i%6])
            m_view = glm.array(mv)
            #depth texture
            for i in range(6):
                self.depth_texture[i].use(location=1+i)
            self.shader_program['m_view_l'].write(m_view.to_bytes())
            self.shadow_program['m_view_l'].write(self.app.lights[0].m_view_l[0])
        else:
            self.shader_program['number_mat'] = [1 for _ in range(4)]
            m_view = glm.array([self.app.lights[0].m_view_l for _ in range(24)])
            #depth texture
            self.depth_texture.use(location=1)
            
            self.shader_program['m_view_l'].write(m_view.to_bytes())
            self.shadow_program['m_view_l'].write(self.app.lights[0].m_view_l)

        self.shadow_program['m_proj'].write(self.camera.m_proj)
        self.shadow_program['m_model'].write(self.m_model)
        #texture part
        self.texture = self.app.mesh.texture.textures[self.tex_id]
        self.shader_program['u_texture_0'] = 0
        
        self.update()

class UI(BaseModel):
    def __init__(self, app, pos=(0,0,0), col=(1,1,1), scale=(1,1,1), tex_id=2, vao_name='ui'):
        super().__init__(app, pos, (0,0,0), scale, tex_id, vao_name)
        self.texture = tex_id
        self.color = glm.vec3(col)
        self.on_init()

    def update(self):
        self.texture.use()
        self.shader_program['pos'].write(self.position)
        self.shader_program['scale'].write(self.scale)
        self.shader_program['color'].write(self.color)

    def on_init(self):
        self.texture = self.app.mesh.texture.textures[self.tex_id]
        self.shader_program['u_texture_0'] = 0
        self.update()

class Letter(BaseModel):
    def __init__(self, app, pos=(0,0,0), col=(1,1,1), main_col=(0,0,0), bg_col=(1,1,1), scale=(1,1,1), tex_id=0, vao_name='letters', number=-1):
        #number allows us to know what it is going to show
        if type(tex_id) != int:
            app.mesh.load_texture_letter(tex_id, col, bg_col) #load both vao and tex
        super().__init__(app, pos, (0,0,0), scale, tex_id, vao_name)
        self.main_color = glm.vec3(main_col)
        self.letter_color = glm.vec3(col)
        self.bg_color = glm.vec3(bg_col)

        self.old_tex_id = "none yet but will be set in futur no worries"
        self.presentation_tex = tex_id
        self.number = number

        self.on_init()

    def update(self):
        self.texture.use()

        self.shader_program['pos'].write(self.position)
        self.shader_program['scale'].write(self.scale)
        self.shader_program['color'].write(self.main_color)
        self.update_writting()
        
        
    def update_writting(self):
        if self.app.camera.selected_obj != None:
            if self.number == 0: 
                self.tex_id = f"{self.app.camera.selected_obj.name}"
            if self.number == 1: 
                self.tex_id = f"({round(self.app.camera.selected_obj.position.x,2)}, {round(self.app.camera.selected_obj.position.y,2)}, {round(self.app.camera.selected_obj.position.z,2)})"
            if self.number == 2:
                self.tex_id = f"({round(self.app.camera.selected_obj.rotation.x,2)}, {round(self.app.camera.selected_obj.rotation.y,2)}, {round(self.app.camera.selected_obj.rotation.z,2)})"
            if self.number == 3:
                self.tex_id = f"({round(self.app.camera.selected_obj.scale.x,2)}, {round(self.app.camera.selected_obj.scale.y,2)}, {round(self.app.camera.selected_obj.scale.z,2)})"
            if self.number == 4:
                self.tex_id = f"{self.app.camera.selected_obj.tex_id}"
            if self.number == 5:
                self.tex_id = f"{self.app.camera.selected_obj.vao_name}"
            if self.number == 6:
                self.tex_id = f"({int(self.app.camera.selected_obj.color.x)}, {int(self.app.camera.selected_obj.color.y)}, {int(self.app.camera.selected_obj.color.z)})"
            if self.number == 7:
                self.tex_id = f"{self.app.camera.selected_obj.intensity}"
            if self.number == 8:
                self.tex_id = f"{round(self.app.fps,0)}"
            if type(self.tex_id) != int and self.old_tex_id != self.tex_id:
                last_int = -len(self.tex_id)

                self.app.mesh.load_texture_letter(self.presentation_tex[:last_int]+self.tex_id, self.letter_color, self.bg_color) #load both vao and tex
                self.old_tex_id=self.tex_id
                self.texture = self.app.mesh.texture.textures[self.presentation_tex[:last_int]+self.tex_id]
                self.shader_program['u_texture_0'] = 0
        else:
            if self.number == 0: 
                self.tex_id = "None"
            if self.number == 1: 
                self.tex_id = "(0, 0, 0)"
            if self.number == 2:
                self.tex_id = "(0, 0, 0)"
            if self.number == 3:
                self.tex_id = "(0, 0, 0)"
            if self.number == 4:
                self.tex_id = "None"
            if self.number == 5:
                self.tex_id = "None"
            if self.number == 6:
                self.tex_id = "(0, 0, 0)"
            if self.number == 7:
                self.tex_id = "None"
            if self.number == 8:
                self.tex_id = f"{round(self.app.fps,0)}"
            if type(self.tex_id) != int and self.old_tex_id != self.tex_id:
                last_int = -len(self.tex_id)

                self.app.mesh.load_texture_letter(self.presentation_tex[:last_int]+self.tex_id, self.letter_color, self.bg_color) #load both vao and tex
                self.old_tex_id=self.tex_id
                self.texture = self.app.mesh.texture.textures[self.presentation_tex[:last_int]+self.tex_id]
                self.shader_program['u_texture_0'] = 0

    def on_init(self):
        #texture part
        self.texture = self.app.mesh.texture.textures[self.tex_id]
        self.shader_program['u_texture_0'] = 0
        self.update()


class Pyramid(BaseModel):
    def __init__(self, app, pos=(0,0,0), rot=(0,0,0), scale=(1,1,1), tex_id=0, vao_name='pyramid', name=None):
        super().__init__(app, pos, rot, scale, tex_id, vao_name, name=name)
        self.on_init()

    def update(self):
        self.texture.use(location = 0)
        #matrices
        self.shader_program['m_proj'].write(self.camera.m_proj)
        self.shader_program['m_view'].write(self.camera.m_view)
        self.shader_program['cam_pos'].write(self.camera.position)
        self.shader_program['m_model'].write(self.m_model)
        #light
        self.buffer_lights()

    def update_shadow(self, indice, face):
        number_mat = []
        number_lights = 0
        m_views = []
        m_proj_ls= []

        for i in range(len(self.app.scene_renderer.shadowMapList)):
            number_lights+=1
            self.depth_texture = self.app.mesh.texture.textures['depth_texture'][i]
            nb = 0
            for e in number_mat:
                nb+=e
            if type(self.depth_texture) == list:
                number_mat.append(6)                    #self.shader_program['number_mat'] = 6
                                                        #m_view = glm.array(self.app.lights[i].m_view_l)
                #depth texture
                for y in range(6):
                    self.depth_texture[y].use(location=1+y+nb)
                    if (len(self.app.lights)>i):
                        m_views.append(self.app.lights[i].m_view_l[y])
            else:
                number_mat.append(1)
                for _ in range(6):
                    m_views.append(self.app.lights[i].m_view_l)
                                                               #m_view = glm.array([self.app.lights[i].m_view_l for _ in range(6)])
                #depth texture
                self.depth_texture.use(location=1+nb)
                
            #self.shader_program['m_view_l'].write(m_view.to_bytes())

            m_proj_ls.append(self.app.lights[i].m_proj_l)

        m_view_l = glm.array(m_views+[glm.mat4() for _ in range(24-len(m_views))])
        m_proj_l = glm.array(m_proj_ls+[glm.mat4() for _ in range(4-len(m_proj_ls))])
        self.shader_program['number_mat'] = np.array(number_mat+[0 for _ in range(4-len(number_mat))])
        self.shader_program['number_lights'] = number_lights
        self.shader_program['m_view_l'].write(m_view_l.to_bytes())
        self.shader_program['m_proj_l'].write(m_proj_l.to_bytes())
        #shadow program (indice)
        if face != -1:
            self.shadow_program['m_view_l'].write(self.app.lights[indice].m_view_l[face])
        else:
            self.shadow_program['m_view_l'].write(self.app.lights[indice].m_view_l)

        self.shadow_program['m_proj'].write(self.app.lights[indice].m_proj_l)
        self.shadow_program['m_model'].write(self.m_model)

    def render_shadow(self, indice, face):
        self.update_shadow(indice, face)
        self.shadow_vao.render()

    def on_init(self):
        #shadow
        self.shadow_vao = self.app.mesh.vao.vaos['shadow_'+self.vao_name]
        self.shadow_program=self.shadow_vao.program

        self.depth_texture = self.app.mesh.texture.textures['depth_texture'][0]
        self.shader_program['shadowMap'] = [i for i in range(1,25)]
        self.shader_program['number_lights'] = 1
        
        if self.app.lights[0].type_of_light == 'point':
            self.shader_program['number_mat'] = [6 for _ in range(4)]
            mv=[]
            for i in range(24):
                mv.append(self.app.lights[0].m_view_l[i%6])
            m_view = glm.array(mv)
            #depth texture
            for i in range(6):
                self.depth_texture[i].use(location=1+i)
            self.shader_program['m_view_l'].write(m_view.to_bytes())
            self.shadow_program['m_view_l'].write(self.app.lights[0].m_view_l[0])
        else:
            self.shader_program['number_mat'] = [1 for _ in range(4)]
            m_view = glm.array([self.app.lights[0].m_view_l for _ in range(24)])
            #depth texture
            self.depth_texture.use(location=1)
            
            self.shader_program['m_view_l'].write(m_view.to_bytes())
            self.shadow_program['m_view_l'].write(self.app.lights[0].m_view_l)

        self.shadow_program['m_proj'].write(self.camera.m_proj)
        self.shadow_program['m_model'].write(self.m_model)
        #texture part
        self.texture = self.app.mesh.texture.textures[self.tex_id]
        self.shader_program['u_texture_0'] = 0
        
        self.update()

class Object(BaseModel):
    def __init__(self, app, pos=(0,0,0), rot=(0,0,0), scale=(1,1,1), tex_id=0, vao_name='cube', vao_link='cube', name = None):
        self.tex_id = vao_name
        if type(tex_id) == int:
            app.mesh.load_texture_obj(vao_name, link=vao_link) #only load vao, no tex
            self.tex_id=tex_id
        else:
            app.mesh.load_texture_obj(vao_name, tex_id, vao_link) #load both vao and tex
        super().__init__(app, pos, rot, scale, self.tex_id, vao_name, set_scale=True, name=name)
        self.on_init()

    def update(self):
        self.texture.use(location = 0)
        #matrices
        self.shader_program['m_proj'].write(self.camera.m_proj)
        self.shader_program['m_view'].write(self.camera.m_view)
        self.shader_program['cam_pos'].write(self.camera.position)
        self.shader_program['m_model'].write(self.m_model)
        #light
        self.buffer_lights()

    def update_shadow(self, indice, face):
        number_mat = []
        number_lights = 0
        m_views = []
        m_proj_ls= []

        for i in range(len(self.app.scene_renderer.shadowMapList)):
            number_lights+=1
            self.depth_texture = self.app.mesh.texture.textures['depth_texture'][i]
            nb = 0
            for e in number_mat:
                nb+=e
            if type(self.depth_texture) == list:
                number_mat.append(6)                    #self.shader_program['number_mat'] = 6
                                                        #m_view = glm.array(self.app.lights[i].m_view_l)
                #depth texture
                for y in range(6):
                    self.depth_texture[y].use(location=1+y+nb)
                    if (len(self.app.lights)>i):
                        m_views.append(self.app.lights[i].m_view_l[y])
            else:
                number_mat.append(1)
                for _ in range(6):
                    m_views.append(self.app.lights[i].m_view_l)
                                                               #m_view = glm.array([self.app.lights[i].m_view_l for _ in range(6)])
                #depth texture
                self.depth_texture.use(location=1+nb)
                
            #self.shader_program['m_view_l'].write(m_view.to_bytes())

            m_proj_ls.append(self.app.lights[i].m_proj_l)

        m_view_l = glm.array(m_views+[glm.mat4() for _ in range(24-len(m_views))])
        m_proj_l = glm.array(m_proj_ls+[glm.mat4() for _ in range(4-len(m_proj_ls))])
        self.shader_program['number_mat'] = np.array(number_mat+[0 for _ in range(4-len(number_mat))])
        self.shader_program['number_lights'] = number_lights
        self.shader_program['m_view_l'].write(m_view_l.to_bytes())
        self.shader_program['m_proj_l'].write(m_proj_l.to_bytes())
        #shadow program (indice)
        if face != -1:
            self.shadow_program['m_view_l'].write(self.app.lights[indice].m_view_l[face])
        else:
            self.shadow_program['m_view_l'].write(self.app.lights[indice].m_view_l)

        self.shadow_program['m_proj'].write(self.app.lights[indice].m_proj_l)
        self.shadow_program['m_model'].write(self.m_model)

    def render_shadow(self, indice, face):
        self.update_shadow(indice, face)
        self.shadow_vao.render()

    def on_init(self):
        #shadow
        self.shadow_vao = self.app.mesh.vao.vaos['shadow_'+self.vao_name]
        self.shadow_program=self.shadow_vao.program

        self.depth_texture = self.app.mesh.texture.textures['depth_texture'][0]
        self.shader_program['shadowMap'] = [i for i in range(1,25)]
        self.shader_program['number_lights'] = 1
        
        if self.app.lights[0].type_of_light == 'point':
            self.shader_program['number_mat'] = [6 for _ in range(4)]
            mv=[]
            for i in range(24):
                mv.append(self.app.lights[0].m_view_l[i%6])
            m_view = glm.array(mv)
            #depth texture
            for i in range(6):
                self.depth_texture[i].use(location=1+i)
            self.shader_program['m_view_l'].write(m_view.to_bytes())
            self.shadow_program['m_view_l'].write(self.app.lights[0].m_view_l[0])
        else:
            self.shader_program['number_mat'] = [1 for _ in range(4)]
            m_view = glm.array([self.app.lights[0].m_view_l for _ in range(24)])
            #depth texture
            self.depth_texture.use(location=1)
            
            self.shader_program['m_view_l'].write(m_view.to_bytes())
            self.shadow_program['m_view_l'].write(self.app.lights[0].m_view_l)

        self.shadow_program['m_proj'].write(self.camera.m_proj)
        self.shadow_program['m_model'].write(self.m_model)
        #texture part
        self.texture = self.app.mesh.texture.textures[self.tex_id]
        self.shader_program['u_texture_0'] = 0
        
        self.update()

class Light(BaseModel):
    def __init__(self, app, light, pos=(0,0,0), rot=(0,0,0), scale=(0.1,0.1,0.1), tex_id=2, vao_name='light', intensity = 1, color = (0,0,0), name=None):
        self.light=light
        self.tex_id = tex_id
        self.intensity = intensity
        self.color = glm.vec3(color)
        super().__init__(app, pos, rot, scale, self.tex_id, vao_name, name = name)
        self.on_init()

    def update(self):
        self.texture.use()
        #matrices
        self.shader_program['m_proj'].write(self.camera.m_proj)
        self.shader_program['m_view'].write(self.camera.m_view)
        self.shader_program['m_model'].write(self.m_model)
        self.shader_program['cam_pos'].write(self.camera.position)

    def on_init(self):
        #texture part
        self.texture = self.app.mesh.texture.textures[self.tex_id]
        self.shader_program['u_texture_0'] = 0
        self.update()