import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from .base import Base

MSG_ERROR = {
    'notnull': 'Field cannot be empty'
}

class Form(Base):

    fields = {}
    validation = {}
    confirm_btn = None
    callback_confirm = None
    callback_cancel = None
    label_error = None

    def __init__(self, **kwargs):
        super(Form, self).__init__()
        """
        validation availables:
            - notnull

        example:
            fields = [
                {'name': 'account_id', 'label': 'Account ID:', validate: ['notnull'] },
                {'name': 'access_key', 'label': 'Access Key:' },
            ]
            initial = {'account_id': '213123'}
            confirm = {'label': 'Save credentials', 'callback': function }
            form = Form(fields=fields, confirm=confirm)
        """

        field_style = Pack(padding=5)
        confirm_style = Pack(padding=5, alignment='right')
        self.label_error = toga.Label('', style=field_style)

        # add form fields
        if 'fields' in kwargs.keys():
            for field in kwargs['fields']:
                # extract data from fields
                name = field['name']
                label = field['label']
                value = ''
                if 'value' in field.keys():
                    value = field['value']
                if 'validate' in field.keys():
                    self.validation = {name: field['validate']}

                # create controls
                label_control = toga.Label(label, style=field_style)
                input_control = toga.TextInput(placeholder='',style=field_style)
                self.getcontrols().add('FormContainer_Label' + name.capitalize() + '', label_control.id)
                self.getcontrols().add('FormContainer_Input' + name.capitalize() + '', input_control.id)

                # add to box
                self.fields[name] = { 'label': label_control, 'input': input_control}
                self.basebox.add(self.fields[name]['label'])
                self.basebox.add(self.fields[name]['input'])

        # Add confirm button
        if 'confirm' in kwargs.keys():
            label, callback = kwargs['confirm'].values()
            self.callback_confirm = callback
            self.confirm_btn = toga.Button(label, 
                                           on_press=self._process_callback,
                                           style=confirm_style)
            self.getcontrols().add('FormContainer_ConfirmButton', self.confirm_btn.id)
            self.basebox.add(self.confirm_btn)

        if 'initial' in kwargs:
            self.set_values(kwargs['initial'])

        # Todo: add cancel button
        self.basebox.add(self.label_error)

    def set_values(self, values):
        for name, field in self.fields.items():
            if name in values:
                field['input'].value = values[name]

    def _write_error(self, error_msg):
        self.label_error.text = error_msg

    def _validate_fields(self):
        for name, field in self.fields.items():
            input = self.fields[name]['input']
            if name in self.validation.keys() and 'notnull' in self.validation[name]:
                if input.value == '':
                    self._write_error(MSG_ERROR['notnull'])
                    return False
                    
        self._write_error('')
        return True

    def _process_callback(self, button):
        if self._validate_fields():
            self.callback_confirm(button)

    def get_field_value(self, field_name):
        return self.fields[field_name]['input'].value