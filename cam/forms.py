from django import forms

from .models import CamSettings


class CamSettingsForm(forms.ModelForm):

    class Meta:
        model = CamSettings

        fields = [
            "camera_no",
            "enabled",
            "cam_name",
            "ip",
            "rtsp_port",
            "username",
            "password",
            "rtsp_path",
        ]

        widgets = {
            "camera_no": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),
            "enabled": forms.CheckboxInput(
                attrs={
                    "class": "form-check",
                }
            ),
            "cam_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Camera Name",
                }
            ),
            "ip": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "192.168.1.100",
                }
            ),
            "rtsp_port": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "554",
                }
            ),
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "off",
                }
            ),
            "password": forms.PasswordInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "new-password",
                },
                render_value=True,
            ),
            "rtsp_path": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "/Streaming/Channels/101",
                }
            ),
        }
