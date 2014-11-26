import curses
import time

from twisted.internet import task
from twisted.internet import reactor

JUMP_DUCK_COOL = 30
JUMP_DUCK_LEN = 20

MOVE_COOL = 1

IMMUNE_COLOR = 6
LIFE_COLOR = 5
LIFE_AMOUNT = 7

LEFT_ACTION = 0
RIGHT_ACTION = 1
PUNCH_ACTION = 2
KICK_ACTION = 3
JUMP_ACTION = 4
DUCK_ACTION = 5

# fighters check cooldowns, game checks boundaries

class Fighter(object):
    def __init__(self, pos=5, right_facing=False, color=1):
        self.right_facing = right_facing
        self.life = LIFE_AMOUNT
        self.pos = pos
        self.jumping = False
        self.ducking = False
        self.punching = False
        self.kicking = False
        self.immune = False
        self.stunned = False
        self.duck_cool = 0
        self.jump_cool = 0
        self.move_cool = 0
        self.punch_cool = 0
        self.kick_cool = 0
        self.stun_cool = 0
        self.color = color

    def draw(self, scr, yline):
        scr.move(yline, self.pos-2)
        scr.addstr(" "*5, curses.color_pair(self.color))
        if self.immune:
            color = IMMUNE_COLOR
        else:
            color = self.color
        if not self.ducking:
            for dy in xrange(-3,0):
                scr.move(yline + dy, self.pos-2)
                scr.addstr(" "*5, curses.color_pair(color))
        if not self.jumping:
            for dy in xrange(1,4):
                scr.move(yline + dy, self.pos-2)
                scr.addstr(" "*5, curses.color_pair(color))
        if self.punching:
            if self.right_facing:
                scr.move(yline-1, self.pos+3)
            else:
                scr.move(yline-1, self.pos-7)
            scr.addstr(" "*5, curses.color_pair(color))
        if self.kicking:
            if self.right_facing:
                scr.move(yline+1, self.pos+3)
            else:
                scr.move(yline+1, self.pos-7)
            scr.addstr(" "*5, curses.color_pair(color))
            for dy in xrange(2,4):
                scr.move(yline + dy, self.pos)
                scr.addstr(" "*5)
        #scr.move(yline+6, self.pos-2)
        #scr.addstr(" "*self.life, curses.color_pair(LIFE_COLOR))

    def left(self):
        if not self.move_cool and not self.punch_cool and not self.kick_cool\
                and not self.stunned:
            self.pos -= 1
            self.move_cool = MOVE_COOL

    def right(self):
        if not self.move_cool and not self.punch_cool and not self.kick_cool\
                and not self.stunned:
            self.pos += 1
            self.move_cool = MOVE_COOL

    def jump(self):
        if not self.jump_cool and not self.kick_cool and not self.ducking\
                and not self.stunned:
            self.jumping = True
            self.jump_cool = 40

    def duck(self):
        if not self.duck_cool and not self.punch_cool and not self.jumping\
                and not self.stunned:
            self.ducking = True
            self.duck_cool = 40

    def punch(self):
        if not self.punch_cool and not self.duck_cool\
                and not self.stunned:
            self.punching = True
            self.punch_cool = 40
            return True
        else:
            if self.punching:
                self.punch_cool = 40
            return False

    def kick(self):
        if not self.kick_cool and not self.jump_cool\
                and not self.stunned:
            self.kicking = True
            self.kick_cool = 60
            return True
        else:
            if self.kicking:
                self.kick_cool = 60
            return False

    def hurt(self, amount=1):
        if not self.immune:
            self.life -= amount
            self.stunned = True
            self.immune = True
            self.stun_cool = 25

    def cooldown(self):
        if self.duck_cool:
            self.duck_cool -= 1
            if self.duck_cool == 20:
                self.ducking = False
        if self.jump_cool:
            self.jump_cool -= 1
            if self.jump_cool == 20:
                self.jumping = False
        if self.move_cool:
            self.move_cool -= 1
        if self.punch_cool:
            self.punch_cool -= 1
            if self.punch_cool == 0:
                self.punching = False
        if self.kick_cool:
            self.kick_cool -= 1
            if self.kick_cool == 0:
                self.kicking = False
        if self.stun_cool:
            self.stun_cool -= 1
            if self.stun_cool == 5:
                self.immune = False
            if self.stun_cool == 0:
                self.stunned = False

class FightGame(object):
    def __init__(self, stdscr, fps=60):
        self.scr = stdscr
        self.chscr = curses.newwin(0,0) # hack to avoid refresh on stdscr
        self.chscr.nodelay(1)
        curses.curs_set(0)
        curses.cbreak()
        curses.use_default_colors()
        curses.init_pair(1, -1, curses.COLOR_YELLOW)
        curses.init_pair(2, -1, curses.COLOR_BLUE)
        curses.init_pair(LIFE_COLOR, -1, curses.COLOR_RED)
        curses.init_pair(IMMUNE_COLOR, -1, curses.COLOR_WHITE)

        self.y, self.x = self.scr.getmaxyx()

        self.lfighter = Fighter(pos=2*self.x/5, right_facing=True, color=1)
        self.rfighter = Fighter(pos=self.x - 2*self.x/5, right_facing=False, color=2)
        self.i = 0

        self.task = task.LoopingCall(self)
        self.task.start(1./fps)
        reactor.run()

    def __call__(self):
        if not reactor.running:
            return
        curses.doupdate()
        self.scr.erase()
        self.y, self.x = self.scr.getmaxyx()
        yline = self.y - 10

        self.lfighter.cooldown()
        self.rfighter.cooldown()

        laction, raction = self.process_chs()

        self.ticks(laction, raction)

        self.lfighter.draw(self.scr, yline)
        self.rfighter.draw(self.scr, yline)

        if self.lfighter.life <= 0 and self.rfighter.life <= 0:
            self.scr.move(self.y/2, self.x/2 - 2)
            self.scr.addstr("TIE!")
            self.scr.noutrefresh()
            curses.doupdate()
            reactor.stop()
        elif self.lfighter.life <= 0:
            self.scr.move(self.y/2, self.x/2 - 5)
            self.scr.addstr("RIGHT WINS!")
            self.scr.noutrefresh()
            curses.doupdate()
            reactor.stop()
        elif self.rfighter.life <= 0:
            self.scr.move(self.y/2, self.x/2 - 5)
            self.scr.addstr("LEFT WINS!")
            self.scr.noutrefresh()
            curses.doupdate()
            reactor.stop()

        self.scr.noutrefresh()

    def process_chs(self):
        laction = raction = None
        ch = self.chscr.getch()
        while ch != -1:
            if ch == ord('a'):
                laction = LEFT_ACTION
            if ch == ord('d'):
                laction = RIGHT_ACTION
            if ch == ord('w'):
                laction = JUMP_ACTION
            if ch == ord('s'):
                laction = DUCK_ACTION
            if ch == ord('c'):
                laction = PUNCH_ACTION
            if ch == ord('x'):
                laction = KICK_ACTION 
            if ch == ord('j'):
                raction = LEFT_ACTION
            if ch == ord('l'):
                raction = RIGHT_ACTION
            if ch == ord('i'):
                raction = JUMP_ACTION
            if ch == ord('k'):
                raction = DUCK_ACTION
            if ch == ord('m'):
                raction = PUNCH_ACTION
            if ch == ord('n'):
                raction = KICK_ACTION 
            ch = self.chscr.getch()
        return laction, raction

    def ticks(self, laction, raction):

        if laction == DUCK_ACTION:
            self.lfighter.duck()

        if laction == JUMP_ACTION:
            self.lfighter.jump()

        if raction == DUCK_ACTION:
            self.rfighter.duck()

        if raction == JUMP_ACTION:
            self.rfighter.jump()

        if laction == LEFT_ACTION:
            if self.lfighter.pos > 3:
                self.lfighter.left()

        if raction == RIGHT_ACTION:
            if self.rfighter.pos < self.x - 3:
                self.rfighter.right()

        if laction == RIGHT_ACTION and raction == LEFT_ACTION:
            if self.rfighter.pos - self.lfighter.pos > 6:
                self.lfighter.right()
                self.rfighter.left()
            else:
                pass
        elif laction == RIGHT_ACTION:
            if self.rfighter.pos - self.lfighter.pos > 5:
                self.lfighter.right()
        elif raction == LEFT_ACTION:
            if self.rfighter.pos - self.lfighter.pos > 5:
                self.rfighter.left()

        if laction == raction == PUNCH_ACTION:
            self.lfighter.punch()
            self.rfighter.punch()
        elif laction == PUNCH_ACTION:
            landed = self.lfighter.punch()
            if landed and self.rfighter.pos - self.lfighter.pos < 11:
                if not self.rfighter.ducking:
                    self.rfighter.hurt()
        elif raction == PUNCH_ACTION:
            landed = self.rfighter.punch()
            if landed and self.rfighter.pos - self.lfighter.pos < 11:
                if not self.lfighter.ducking:
                    self.lfighter.hurt()

        if laction == raction == KICK_ACTION:
            self.lfighter.kick()
            self.rfighter.kick()
        elif laction == KICK_ACTION:
            landed = self.lfighter.kick()
            if landed and self.rfighter.pos - self.lfighter.pos < 11:
                if not self.rfighter.jumping:
                    self.rfighter.hurt(amount=2)
        elif raction == KICK_ACTION:
            landed = self.rfighter.kick()
            if landed and self.rfighter.pos - self.lfighter.pos < 11:
                if not self.lfighter.jumping:
                    self.lfighter.hurt(amount=2)

if __name__ == "__main__":
    curses.wrapper(FightGame)
