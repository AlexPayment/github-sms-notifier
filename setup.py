from distutils.core import setup

setup(name='GitHubSmsNotifier',
      version='0.1',
      description='SMS notifier for GitHub',
      author='Alexandre Payment',
      packages=['github-sms-notifier'],
      install_requires=['Flask==0.10.1',
                        'requests==2.2.1',
                        'twilio==3.6.6'],
)
