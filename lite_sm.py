# -*- coding: utf-8 -*-

__author__ = "xiechao"
__author_email__ = "xiechao06@gmail.com"
__version__ = "0.9.0"

import types

class InvalidAction(Exception):
    code = 30004
    name = "invalid-action"

    def __init__(self, description=None):
        Exception.__init__(self, '%d %s' % (self.code, self.name))
        if description is not None:
            if isinstance(description, types.StringType):
                description = description.decode("utf-8")
            self.description = description

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        if 'description' in self.__dict__:
            txt = self.description
        else:
            txt = self.name
        return u'%d: %s' % (self.code, txt)

    def __repr__(self):
        return '<%s \'%s\'>' % (self.__class__.__name__, self)

    def get_avail_actions(self, ignore_perm=True):
        raise NotImplementedError()

class State(object):

    status = None
    
    def __init__(self, sm, rule_map, actors=[]):
        self.actors = actors
        self.rule_map = rule_map
        self.sm = sm
        if not hasattr(self.sm, "status_map"):
            self.sm.status_map = {}
        self.sm.status_map[self.status] = self

    @property
    def last_status(self):
        return self.sm.last_state.status

    def next(self, input):
        next_status, perm = self.rule_map[input]
        if perm:
            perm.test()
        try:
            return self.sm.status_map[next_status]
        except KeyError:
            raise InvalidAction(self.sm.invalid_info(input, self))

    def get_avail_actions(self, ignore_perm=True):
        ret = self.rule_map.keys()
        if not ignore_perm:
            ret = [action for action in ret if self.rule_map["action"][1].can()]
        return ret 

    def side_effect(self):
        pass

class StateMachine(object):
    def __init__(self, obj=None, logger=None):
        self.obj = obj
        self.logger = logger

    def set_init_state(self, init_state):
        self.current_state = init_state

    def next(self, action, actor=None, *args, **kwargs):
        last_state = self.current_state
        self.current_state = last_state.next(action)
        self.current_state.last_state = last_state
        self.current_state.action = action
        self.current_state.sm = self
        self.current_state.side_effect(*args, **kwargs)

        # notify the actors
        for actor_ in self.current_state.actors:
            self.sm.notify_next_actor(actor_)

        # log
        if self.logger:
            msg = repr(self.obj)+"'s " if self.obj else ""
            msg += "state has changed from %s to %s " % (repr(last_state), repr(self.current_state))
            msg += "by " + repr(actor) 
            self.logger.info(msg, extra={"obj": self.obj, "actor": actor, "last_state": last_state, "current_state": self.current_state, "action": action})
    
    def get_avail_actions(self, ignore_perm=True):
        return self.current_state.get_avail_actions(ignore_perm)
                
    def notify_next_actor(self, actor):
        pass

    def invalid_info(self, input, state):
        return u"%(status)s状态不允许进行%(action)s操作" % {"action": unicode(input), "status": unicode(state.status)}


if __name__ == "__main__":
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(fmt='%(asctime)s [%(levelname)s]:%(message)s', 
                                  datefmt='%m/%d/%Y %I:%M:%S %p')
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    class TrafficLight(object):

        def __init__(self, color):
            self.color = color

        def __repr__(self):
            return "<TrafficLight color:%s>" % self.color
    
    tl = TrafficLight("green")
    
    red_status = 0
    green_status = 1
    yello_status = 2

    sm = StateMachine(tl, logger)
    
    class RedState(State):
        status = red_status

        def side_effect(self, *args, **kwargs):
            self.sm.obj.color = "red"

        def __repr__(self):
            return "<RedState>"

    class GreenState(State):
        status = green_status

        def side_effect(self, *args, **kwargs):
            self.sm.obj.color = "green"

        def __repr__(self):
            return "<GreenState>"

    class YellowState(State):
        status = yello_status

        def side_effect(self, *args, **kwargs):
            self.sm.obj.color = "yellow"

        def __repr__(self):
            return "<YellowState>"
    
    red_state = RedState(sm, {"turn_green": (green_status, None)})
    green_state = GreenState(sm, {"turn_yellow": (yello_status, None)})
    yellow_state = YellowState(sm, {"turn_red": (red_status, None)})
    sm.set_init_state(green_state)

    print "available actions -- " + ",".join(sm.get_avail_actions())
    print "turn yellow"
    sm.next("turn_yellow", "hujintao")
    print "current color is -- " + tl.color
    print "available actions -- " + ",".join(sm.get_avail_actions())
    print "turn red"
    sm.next("turn_red", "xijinping")
    
