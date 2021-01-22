class RenderingProperty:
    def __init__(self, name):
        self.name = name
        self.attr_name = f"_{self.name}"

    def __get__(self, instance, owner):
        if instance is not None:
            return getattr(instance, self.attr_name, None)

    def __set__(self, instance, value):
        if instance is not None:
            setattr(instance, self.attr_name, value)
            instance.requires_render = True
