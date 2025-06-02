# Author: JJ Kullberg
# Completed May 7, 2025
# Purpose: GEOG 498 term project, GUI event handler

import sys, os
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
import main
import csv_analyzer

# Initialize app and main window
app = QApplication(sys.argv)
mainWindow = QMainWindow()
# Create instance of main ui class, and call set up method
ui = main.Ui_MainWindow()
ui.setupUi(mainWindow)

# ====================================================================================================================

# Base variables
geometryList = ['Point', 'Polyline', 'Polygon']
defaultSR = '4326'
currentInstance = None
selectedFields = []

for geometry in geometryList:
    ui.featureTypeCB.addItem(geometry)

ui.spatialReferenceLE.setText(defaultSR)

# Event handler functions

def selectCSV():
    """open file dialog to select a CSV file elements, populate csv line edit with file path"""
    fileName, _ = QFileDialog.getOpenFileName(
        mainWindow,
        "Select CSV",
        "",
        "CSV(*.csv)"
    )
    if fileName:
        ui.selectCSVLE.setText(fileName)

def shapefileOutput():
    """open save file dialog to select output location for the shapefile"""
    fileName, _ = QFileDialog.getSaveFileName(
        mainWindow,
        "Save shapefile output as",
        "",
        "Shapefile(*.shp)"
    )
    if fileName:
        ui.selectShapefileLE.setText(fileName)

def setCurrentInstance():
    """Make a new instance of a Processor object with the selected CSV file"""
    try:
        global currentInstance # Access global currentInstance variable
        # Check which geometry is selected in the feature type combo box, and create instance with the
        # corresponding class
        if ui.featureTypeCB.currentText() == 'Point':
            currentInstance = csv_analyzer.PointProcessor(ui.selectCSVLE.text())
        elif ui.featureTypeCB.currentText() == 'Polyline':
            currentInstance = csv_analyzer.PolylineProcessor(ui.selectCSVLE.text())
        else:
            currentInstance = csv_analyzer.PolygonProcessor(ui.selectCSVLE.text())
    except:
        currentInstance = None # Set currentInstance to None if the line edit text is not viable

def clearListWidget():
    """Clear out list of selected fieldItems and their displayed names in the list widget"""
    selectedFields.clear()
    ui.selectedFieldsLW.clear()

def clearAll():
    """Clear all combo boxes, list widget, and selection list"""
    ui.latitudeCB.clear()
    ui.longitudeCB.clear()
    ui.selectFieldCB.clear()
    ui.nodeFieldCB.clear()
    clearListWidget()

# Functions to be called by populateFieldCBS()

def pointSelectFields():
    """When feature type is point and all fields checkbox is off"""
    for item in currentInstance.fields:
        ui.latitudeCB.addItem(item)
        ui.longitudeCB.addItem(item)
        ui.selectFieldCB.addItem(item)

def pointAllFields():
    """When feature type is point and all fields checkbox is on"""
    for item in currentInstance.fields:
        ui.latitudeCB.addItem(item)
        ui.longitudeCB.addItem(item)
    ui.selectFieldCB.addItem('All Fields')

def polySelectFields():
    """When feature type is poly and all fields checkbox is off"""
    for item in currentInstance.fields:
        ui.nodeFieldCB.addItem(item)
        ui.selectFieldCB.addItem(item)

def polyAllFields():
    """When feature type is poly and all fields checkbox is on"""
    for item in currentInstance.fields:
        ui.nodeFieldCB.addItem(item)
    ui.selectFieldCB.addItem('All Fields')

def populateFieldCBS():
    """Populate combo boxes according to which feature type is selected"""
    if currentInstance != None:
        if ui.featureTypeCB.currentText() == 'Point':
            if ui.addAllFieldsCB.isChecked():
                pointAllFields()
            else:
                pointSelectFields()
        else:
            if ui.addAllFieldsCB.isChecked():
                polyAllFields()
            else:
                polySelectFields()
    else:
        if ui.addAllFieldsCB.isChecked():
            ui.selectFieldCB.addItem('All Fields')

def csvLineEditTextChanged():
    """Action to take if text in csv line edit changes"""
    clearAll()
    setCurrentInstance()
    populateFieldCBS()

def featureTypeChanged():
    """Action to take if selection in the feature type cb changes"""
    clearAll()
    setCurrentInstance()
    populateFieldCBS()

def checkAddAllFieldsCB():
    """Function to be called when all fields check box is toggled"""
    # Clear field select CB and add 'All Fields' if toggled on
    if ui.addAllFieldsCB.isChecked():
        ui.selectFieldCB.clear()
        clearListWidget()
        ui.selectFieldCB.addItem('All Fields')
    # Repopulate field select with fields from the current df if toggled off
    else:
        ui.selectFieldCB.clear()
        if currentInstance != None: # Check that a valid object can be created from text in csv LE # Current instance
            for item in currentInstance.fields: # Add all column names to field select CB if so # Current instance
                ui.selectFieldCB.addItem(item)
        else:
            pass # Field select CB remains blank if there is no current df


def selectFields():
    """Add field item to fields list when item is selected from the fields combobox, and display name in the LW"""
    field = ui.selectFieldCB.currentText() # Access selected field name
    if field not in selectedFields and field != "All Fields": # Check that item has not been previously selected
        selectedFields.append(field) # Add to list of fieldItem objects
        ui.selectedFieldsLW.addItem(field) # Display in selected fields list widget


def createShapefile():
    """Call the method that creates a new shapefile, and provide it with the selected parameters"""

    try:

        if ui.addAllFieldsCB.isChecked(): # Check if user has selected the All Fields checkbox
            # If the checkbox is toggled, the field_list variable is assigned an instance variable from class CSVConverter
            #   that contains a list of all column names as fieldItem objects
            field_list = currentInstance.fieldObjects
        else:
            # If checkbox is not toggled, field_list is assigned the list of fieldItem objects individually selected by user
            field_list = csv_analyzer.FieldItem.fromColumnNames(selectedFields)

        # Check if current instance is point or polyline/polygon, and add geometry
        if ui.featureTypeCB.currentText() == 'Point':
            currentInstance.addGeometry(
                latField=ui.latitudeCB.currentText(),
                lonField=ui.longitudeCB.currentText(),
            )
        else:
            currentInstance.addGeometry(
                nodeField=ui.nodeFieldCB.currentText(),
            )
        # Call the create shapefile method
        currentInstance.createShapefile(
        wkid=ui.spatialReferenceLE.text(),
        output=ui.selectShapefileLE.text(),
        fields=field_list
        )

        # Get shapefile basename for success message
        shapefileName = os.path.basename(ui.selectShapefileLE.text())
        # Add success message after shapefile creation
        QMessageBox.information(
            mainWindow, "Success",
            f"Successfully created {shapefileName}.",
            QMessageBox.Ok)


    except Exception as e:
        if e.name == 'addGeometry':
            errorMessage = "Please select a valid CSV file"
            QMessageBox.information(mainWindow, "Error", f"{errorMessage}", QMessageBox.Ok)
        else:
            QMessageBox.information(mainWindow, "Error", f"{e}", QMessageBox.Ok)

# =====================================================================================================================

# Connect signals
ui.selectCSVTB.clicked.connect(selectCSV) # When the select csv file tool button is clicked
ui.selectShapefileTB.clicked.connect(shapefileOutput) # When the select output shapefile tool button is clicked
ui.selectCSVLE.textChanged.connect(csvLineEditTextChanged) # When the text in the select csv line edit is changed
ui.addAllFieldsCB.toggled.connect(checkAddAllFieldsCB) # When the all fields checkbox is toggled
ui.featureTypeCB.currentTextChanged.connect(featureTypeChanged) # When a new feature type is selected
ui.clearSelectionPB.clicked.connect(clearListWidget) # When the clear list widget button is clicked
ui.selectFieldCB.textActivated.connect(selectFields) # When an item from the field combo box is selected
ui.runPB.clicked.connect(createShapefile) # When the run button is clicked


# Run app
mainWindow.show()
sys.exit(app.exec_())
