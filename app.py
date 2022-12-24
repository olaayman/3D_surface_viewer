import sys
import vtk
from PyQt5 import QtCore, QtWidgets
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtk.util.numpy_support import vtk_to_numpy, numpy_to_vtk
from skimage.exposure import equalize_hist

from PyQt5.uic import loadUiType
import os 
import sys
import pydicom as dicom # For reading dicom image
import numpy as np
from PyQt5 import QtCore
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib 
matplotlib.use('Qt5Agg')
from PyQt5.QtGui import * 
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUiType
import os 
import scipy.io


ui,_ = loadUiType(os.path.join(os.path.dirname(__file__),'GUI.ui'))

class MainWindow(QtWidgets.QMainWindow, ui):
 
    def __init__(self, parent = None):
        super().__init__()
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.renderWindowInteractor = QVTKRenderWindowInteractor(self.frame_3D)
        self.renderer = vtk.vtkRenderer()
        self.renderWindowInteractor.GetRenderWindow().AddRenderer(self.renderer)
        self.iren = self.renderWindowInteractor.GetRenderWindow().GetInteractor()
        self.Slice_renderWindowInteractor = QVTKRenderWindowInteractor(self.frame_2D)
        self.slice_renderer = vtk.vtkRenderer()
        self.Slice_renderWindowInteractor.GetRenderWindow().AddRenderer(self.slice_renderer)
        self.Slice_renderWindowInteractor.GetRenderWindow().SetSize(160, 160)
        self.iren2 = self.Slice_renderWindowInteractor.GetRenderWindow().GetInteractor()
        
        #variables
        self.z_spacing = 5
        self.slice_num = self.sliceSelectSlider.value()
        self.imgData = []
        self.readers = []
        self.mappers = []
        self.actors = []
        self.transforms = []
        self.number_of_slices = 15
        self.thresh = 0
        
        self.colors = vtk.vtkNamedColors()
        self.mapping_matrix = [-1.5625, -0.0, 0.0, 0.0,
                                -0.0, -1.5625, 0.0, 0.0,
                                0.0, 0.0, 1.5625, 0.0,
                                0, 0, 0, 1]

        #Read The Data
        self.data_dict = scipy.io.loadmat('Dataset Intro/12_comboBI_pLGE_05_image.mat')
        
        #Slider to change the slice
        self.sliceSelectSlider.valueChanged.connect(self.changeSlice)
        #Histogram Slider
        self.thresholdSelectSlider.valueChanged.connect(self.ChangeThreshold)
        self.set_sliders_limits()
        # show Volume button
        self.cameraChange = True
        self.showVolume_Button.clicked.connect(self.Render_3D_Surface)

        #3D point
        self.point = vtk.vtkPointSource()
        self.point.SetCenter(216,256,0)
        self.point.SetRadius(0)

        point_mapper = vtk.vtkPolyDataMapper()
        point_mapper.SetInputConnection(self.point.GetOutputPort())
        point_actor = vtk.vtkActor()
        point_actor.SetMapper(point_mapper)
        point_actor.GetProperty().SetColor(self.colors.GetColor3d("Red"))
        point_actor.GetProperty().SetPointSize(5)
        #print(point_actor.GetProperty())

        point_transform = vtk.vtkTransform()
        point_transform.SetMatrix(self.mapping_matrix)
        point_actor.SetUserTransform(point_transform)
        self.renderer.AddActor(point_actor)

        #2D point
        self.Slice_renderWindowInteractor.SetInteractorStyle(vtkInteractorStyleTrackballCamera())
        self.point_2D = vtk.vtkPointSource()

        self.Slice_renderWindowInteractor.RemoveObservers('LeftButtonPressEvent')
        self.Slice_renderWindowInteractor.AddObserver('LeftButtonPressEvent', self.OnClick, 1.0)

        #Histo Axes
        self.histo_scene = QGraphicsScene()
        self.histo_canvas = FigureCanvas(Figure(figsize=(4, 2)))
        self.histo_ax = self.histo_canvas.figure.subplots()
        self.histo_scene.addWidget(self.histo_canvas)
        self.Histo_graphicsView.setScene(self.histo_scene)



        self.Render_3D_Surface()
        self.renderer.ResetCamera()

        self.Render_2D_Slice()
        self.slice_renderer.ResetCamera()
 
        self.show()
        self.iren.Initialize()
        self.iren2.Initialize()

        
        
        #self.iren2.Start()


    def closeEvent(self, QCloseEvent):
        super().closeEvent(QCloseEvent)
        self.renderWindowInteractor.close()
        self.Slice_renderWindowInteractor.close()

    def ChangeThreshold(self):
        self.thresh = self.thresholdSelectSlider.value()
        self.DrawHistogram()
        self.Render_Diffuse_Scar()

    def DrawHistogram(self):
        self.histo_scene = QGraphicsScene()
        self.histo_canvas = FigureCanvas(Figure(figsize=(4, 2)))
        self.histo_ax = self.histo_canvas.figure.subplots()
        print("in draw histo")
        self.histo_ax.axvline(x = self.thresh, color = 'b', label = 'axvline - full height')
        self.histo_ax.set_ylim([0, 0.03])
        # print("flatten",self.imgData[self.slice_num].flatten())
        # print("not flatten",self.imgData[self.slice_num])
        self.histo_ax.hist(self.imgData[self.slice_num].flatten(), 256, density=1, facecolor="green")
        #print(n)
        self.histo_scene.addWidget(self.histo_canvas)
        self.Histo_graphicsView.setScene(self.histo_scene)

        

    def OnClick(self,obj, ev):

        print('Before Event')
        print(obj.GetEventPosition())
        # - 120 because the 2D actor is shifted by 120
        self.point.SetCenter(obj.GetEventPosition()[0]-120,obj.GetEventPosition()[1]-200,-self.slice_num * self.z_spacing)
        self.point_2D.SetCenter(obj.GetEventPosition()[0],obj.GetEventPosition()[1],0)
        self.point_2D.SetRadius(0)
        point_mapper_2D = vtk.vtkPolyDataMapper2D()
        point_mapper_2D.SetInputConnection(self.point_2D.GetOutputPort())
        point_actor_2D = vtk.vtkActor2D()
        point_actor_2D.SetMapper(point_mapper_2D)
        point_actor_2D.GetProperty().SetColor(self.colors.GetColor3d("Blue"))
        point_actor_2D.GetProperty().SetPointSize(3)

        self.slice_renderer.AddActor(point_actor_2D)
        self.renderWindowInteractor.GetRenderWindow().Render()

    def set_sliders_limits(self):
        self.sliceSelectSlider.setValue(0)
        self.sliceSelectSlider.setTickInterval(1)
        self.sliceSelectSlider.setMinimum(0)
        self.sliceSelectSlider.setMaximum(self.number_of_slices-1)

        self.thresholdSelectSlider.setValue(0)
        self.thresholdSelectSlider.setTickInterval(1)
        self.thresholdSelectSlider.setMinimum(0)
        self.thresholdSelectSlider.setMaximum(255)

    def changeSlice(self):
        my_value = self.sliceSelectSlider.value()
        self.slice_num = my_value
        self.Render_2D_Slice()
        
        self.Slice_renderWindowInteractor.GetRenderWindow().Render()
        print(my_value)


    def Render_2D_Slice(self):
        # Load MAt images
        # data_dict = scipy.io.loadmat('Dataset Intro/12_comboBI_pLGE_05_image.mat')
        # print("mat images", data_dict.keys())
        # print("mat images shapes", data_dict['tmp_vol_im'].max())
        # data_vtk = numpy_to_vtk(num_array=data_dict['tmp_vol_im'][:,:,1,9].ravel(), deep=True, array_type=vtk.VTK_FLOAT)
        # image_vtk = vtk.vtkImageData()
        # image_vtk.SetDimensions([160,160,1])
        # image_vtk.SetSpacing(np.array([1.0, 1.0, 2.0]))
        # image_vtk.GetPointData().SetScalars(data_vtk)

        #print("getoutput type", type(self.readers[self.slice_num].GetOutput()))
        # Render the image
        slice_mapper = vtk.vtkImageMapper()
        #slice_mapper.SetInputData(image_vtk)
        slice_mapper.SetInputData(self.readers[self.slice_num])
        # color window = max intensity in the image and color level is its half
        slice_mapper.SetColorWindow(255)
        slice_mapper.SetColorLevel(127.5)

        slice_actor = vtk.vtkActor2D()
        #to put the image in the center of the window
        slice_actor.SetPosition(120,200)
        slice_actor.SetMapper(slice_mapper)

        self.slice_renderer.AddActor(slice_actor)
        self.slice_renderer.ResetCamera()
        # self.slice_renderer.ResetCameraClippingRange()
        
        #Draw Histogram
        self.DrawHistogram()




    def Render_3D_Surface(self):
        for i in range(self.number_of_slices):
            # reader = vtk.vtkPNGReader()
            # reader.SetFileName("dataset/slice"+str(i+1)+".png")
            # reader.Update()
            if len(self.imgData) < self.number_of_slices:
                scaled_Img = ((self.data_dict['tmp_vol_im'][:,:,1,i] - self.data_dict['tmp_vol_im'][:,:,1,i].min()) * (1/(self.data_dict['tmp_vol_im'][:,:,1,i].max() - self.data_dict['tmp_vol_im'][:,:,1,i].min()) * 255))
                self.imgData.append(scaled_Img)
                data_vtk = numpy_to_vtk(num_array=scaled_Img.ravel(), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
                image_vtk = vtk.vtkImageData()
                image_vtk.SetDimensions([160,160,1])
                image_vtk.SetSpacing(np.array([1.0, 1.0, 1.0]))
                image_vtk.GetPointData().SetScalars(data_vtk)
                self.readers.append(image_vtk)


            mapper = vtk.vtkDataSetMapper()
            mapper.SetInputData(self.readers[i])
            self.mappers.append(mapper)

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)

            transform = vtk.vtkTransform()
            transform.SetMatrix(self.mapping_matrix)
            transform.Translate(0, 0, -i*self.z_spacing)
            actor.SetUserTransform(transform)
            self.actors.append(actor)
            self.transforms.append(transform)

            self.renderer.AddActor(actor)

        if self.cameraChange:
            cameratransform = vtk.vtkTransform()
            cameratransform.RotateX(180)
            cameratransform.RotateY(180)
            cameratransform.RotateZ(0)
            self.renderer.GetActiveCamera().ApplyTransform(cameratransform)
            self.cameraChange = False

        self.renderer.ResetCamera()

        self.renderWindowInteractor.GetRenderWindow().Render()


    def Render_Diffuse_Scar(self):
        for i in range(self.number_of_slices):
            # reader = vtk.vtkPNGReader()
            # reader.SetFileName("dataset/slice"+str(i+1)+".png")
            # reader.Update()
            # self.readers.append(reader)
            # im = self.readers[i].GetOutput()
            # sc = im.GetPointData().GetScalars()
            # a = vtk_to_numpy(sc)
            # print("slice" ,a.shape)
            contour = np.where(self.imgData[i] > self.thresh, 255 ,0)
            data_vtk = numpy_to_vtk(num_array=contour.ravel(), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
            image_vtk = vtk.vtkImageData()
            image_vtk.SetDimensions([160,160,1])
            image_vtk.SetSpacing(np.array([1.0, 1.0, 1.0]))
            image_vtk.GetPointData().SetScalars(data_vtk)

            mapper = vtk.vtkDataSetMapper()
            mapper.SetInputData(image_vtk)
            self.mappers.append(mapper)

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)

            transform = vtk.vtkTransform()
            transform.SetMatrix(self.mapping_matrix)
            transform.Translate(0, 0, -i*self.z_spacing)
            actor.SetUserTransform(transform)
            self.actors.append(actor)
            self.transforms.append(transform)

            self.renderer.AddActor(actor)

        # cameratransform = vtk.vtkTransform()
        # cameratransform.RotateX(180)
        # cameratransform.RotateY(180)
        # cameratransform.RotateZ(0)
        # self.renderer.GetActiveCamera().ApplyTransform(cameratransform)

        self.renderer.ResetCamera()

        self.renderWindowInteractor.GetRenderWindow().Render()


if __name__ == "__main__":
 
    app = QtWidgets.QApplication(sys.argv)
 
    window = MainWindow()
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1" 
    window.show()
    sys.exit(app.exec_())