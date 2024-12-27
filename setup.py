#!/usr/bin/env python

from setuptools import find_packages, setup

with open('README.md') as f:
    long_description = f.read()

setup(name="pipelinewise-target-snowflake",
      version="2.3.0",
      description="Singer.io target for loading data to Snowflake - PipelineWise compatible",
      long_description=long_description,
      long_description_content_type='text/markdown',
      author="Wise",
      url='https://github.com/transferwise/pipelinewise-target-snowflake',
      classifiers=[
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 3 :: Only',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
      ],
      py_modules=["target_snowflake"],
      python_requires='>=3.7',
      install_requires=[
          'pipelinewise-singer-python==1.*',
          # 3.4.0 Removed dependencies on pycryptodomex and oscrypto. All connections now go through OpenSSL via the cryptography library, which was already a dependency.
          # https://github.com/snowflakedb/snowflake-connector-python/blob/f323d22bf259a176f6c57510efd4927c52f1abb9/DESCRIPTION.md?plain=1#L37
          # This should prevent 'Error detecting the version of libcrypto':
          # https://github.com/wbond/oscrypto/issues/75
          'snowflake-connector-python[pandas,secure-local-storage]==3.4.0',
          'inflection==0.5.1',
          'joblib==1.2.0',
          'boto3==1.28.20',
          # Pinning numpy to latest pre-2.0.0 version, per recommendation:
          # https://stackoverflow.com/a/78641304
          # since pandas otherwise triggers a >=2.0.0 install, which produces a set of problems (binary incompatibility
          # for snowflake-connector-python==3.0.4, segmentation fault on macOS for more recent versions) that don't
          # currently seem possible to fully resolve cross-platform.
          'numpy==1.26.4',
      ],
      extras_require={
          "test": [
              "pylint==2.12.*",
              'pytest==7.4.0',
              'pytest-cov==3.0.0',
              "python-dotenv>=0.19,<1.1"
          ]
      },
      entry_points="""
          [console_scripts]
          target-snowflake=target_snowflake:main
      """,
      packages=find_packages(exclude=['tests*']),
      )
