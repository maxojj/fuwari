---
title: TrueNAS中手动更新Plex
english_slug: plexontruenas
published: 2021-06-21 21:30:00
description: 基于TureNAS的Plex使用小技巧
image: ''
tags:
  - 科技
category: 生活日常
draft: false
---

## 背景

TrueNAS是我自用NAS使用的免费系统，基于FreeBSD开发，拥有类似于Docker的“Jail”功能，即可以在系统中安装运行某些虚拟服务。既然是家用NAS，自然少不了影音管理，且TureNAS官方就提供了Plex的安装包，所以Plex成为了我的主力影音管理平台。

但问题在于，TrueNAS所提供的Plex安装包并非官方版本，而是其自行适配后放出的兼容版本。这就会有一个时间差，也就是说，Plex官方软件更新，到TrueNAS提供软件更新之间，至少有以月为单位的延迟。。。（此为个人经验，仅供参考）

这个问题并不算致命，但使用中的一些小Bug，包括官方提示更新的「小黄点」，都在无时无刻提醒你与最新版本之间的差距。

我一直尝试容忍这样的问题存在，直到我发现Plex官方是提供了FreeBSD的安装包的，且因为同源的关系，TrueNAS上完全可以运行。于是广大网友通过脚本的方式，算是“hack”了软件的升级方式。

## 成本

整个配置过程，只要你的网络足够科学，应该不会多于10分钟。配置完成后，只要提示升级，只需要手动跑一行代码，或者设置TrueNAS一个定时任务（系统自带功能）即可。

## 方法

- 首先，你需要在“Jail”中安装官方提供的Plex软件，并且完成所有配置，上线运行
- 接下来，在运行的Plex条目上点击右侧的箭头，出现下拉菜单，在其中选择「命令行」选项
    - 应该很好理解，现在的Plex就是一个虚拟机，而你进入的，就是这个虚拟机对应的“shell”命令行
- 接下来，就是复制粘贴一些命令。首先，需要安装一些依赖

```plain
pkg install wget
pkg install ca_root_nss
pkg install perl

```

- 接下来，创建一个目录用来储存脚本，以及完成下载

```plain
mkdir /usr/local/PMS_Updater
cd /usr/local/PMS_Updater
wget <https://raw.githubusercontent.com/mstinaff/PMS_Updater/master/PMS_Updater.sh>

```

- 好了，准备工作这就全部完成。现在可以运行脚本了，运气好的话，一次成功，你的Plex也就成为了最新版本

```plain
sh PMS_Updater.sh -v -a

```

运行这行命令后，你可以看到程序的反馈。如果网络不太好，有可能下载失败，重新运行一遍命令即可。几周后如果想要更新，还是重新运行一次这个命令就可以了，非常方便。

## 我遇到的问题

目前遇到的唯一问题，是关于python版本的问题，起因我猜测跟TrueNAS系统更新有关，2.7版本的python不再支持，导致脚本一运行就报错

```plain
ImportError: No module named site
Could not find a FreeBSD download link on page <https://plex.tv/api/downloads/5.json?channel=plexpass&X-Plex-Token=>...

```

如果你也出现同样的报错信息，可以在下面的issue页面尝试修改方法，很多开发在里面讨论，毕竟本身不是个很复杂的问题。

[ImportError: No module named site · Issue #57 · mstinaff/PMS_Updater](https://github.com/mstinaff/PMS_Updater/issues/57)

差不多先这样，TrueNAS系统本身也可以聊聊。相比较黑群晖，作为正版授权的免费软件，省下很多折腾人的事情，同时暂时也满足了我对NAS的需求。虽然界面没有群晖那么赏心悦目，但在国内我觉得是被低估的。
