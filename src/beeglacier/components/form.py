import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

class Form:

    basebox = None
    fields = {}
    confirm_btn = None
    callback_confirm = None
    callback_cancel = None

    def __init__(self, **kwargs):
        """
        example:
            fields = [
                {'name': 'account_id', 'label': 'Account ID:' },
                {'name': 'access_key', 'label': 'Access Key:' },
            ]
            confirm = {'label': 'Save credentials', 'callback': function }
            form = Form(fields=fields, confirm=confirm)
        """

        self.basebox = toga.Box(style=Pack(direction=COLUMN, flex=1, padding=5))
        field_style = Pack(padding=5)
        confirm_style = Pack(padding=5, alignment='right')

        # add form fields
        if 'fields' in kwargs.keys():
            for field in kwargs['fields']:
                # extract data from fields
                name = field['name']
                label = field['label']
                value = ''
                if 'value' in field.keys():
                    value = field['value']

                # create controls
                label_control = toga.Label(label, style=field_style)
                input_control = toga.TextInput(placeholder='',style=field_style)
                input_control.value = value

                # add to box
                self.fields[name] = { 'label': label_control, 'input': input_control }
                self.basebox.add(self.fields[name]['label'])
                self.basebox.add(self.fields[name]['input'])

        # Add confirm button
        if 'confirm' in kwargs.keys():
            label, callback = kwargs['confirm'].values()
            self.confirm_btn = toga.Button(label, 
                                           on_press=callback,
                                           style=confirm_style)
            self.basebox.add(self.confirm_btn)

        # Todo: add cancel button

    def getbox(self):
        return self.basebox

    def get_field_value(self, field_name):
        return self.fields[field_name]['input'].value