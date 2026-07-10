from django import forms

from .models import CamSettings


class CamSettingsForm(forms.ModelForm):

    rtsp_url = forms.CharField(
        label="RTSP URL",
        required=False,
        disabled=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        )
    )

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
            "min_confidence",
            "min_width",
            "min_height",
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

            "min_confidence": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0.5",
                }
            ),

            "min_width": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "300",
                }
            ),

            "min_height": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "70",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields["rtsp_url"].initial = self.instance.rtsp_url
